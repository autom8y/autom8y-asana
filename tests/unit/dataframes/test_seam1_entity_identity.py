"""SEAM-1 entity-identity key contract — adversarial / broken-fixture proofs.

ADR-SEAM1. These tests are the G-THEATER proof obligations: each one fails RED
against the OLD (entity-agnostic) behavior and passes GREEN only because the
entity-identity key is threaded end-to-end.

Proof obligations exercised here:
  1. Cross-entity collision (the telos, G-DENOM): a section-shaped frame written
     to project P under entity 'section' MUST NOT clobber the offer frame written
     to the SAME project P under entity 'offer'. The deliberately-broken
     companion (BOTH writes to the legacy entity-AGNOSTIC key) DOES collide --
     proving the entity-key is what prevents it.
  2. Present-but-null receipt (FM-4): a 62-row active offer frame whose ``mrr`` is
     entirely null fires ``population_receipt_below_floor`` RED; a populated frame
     does not.
  3. FM-2 status: a section/project fixture task with a 'Status' custom field
     produces a non-null ``status`` (was 100% null under source=None).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

import polars as pl

from autom8_asana.config import S3LocationConfig
from autom8_asana.core.retry import (
    BudgetConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    DefaultRetryPolicy,
    RetryBudget,
    RetryOrchestrator,
    RetryPolicyConfig,
    Subsystem,
)
from autom8_asana.dataframes.builders.post_build_population_receipt import (
    POPULATION_WARN_THRESHOLD,
    post_build_population_receipt,
)
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from autom8_asana.dataframes.storage import S3DataFrameStorage

# asyncio_mode="auto" (pyproject) -> async defs run without an explicit marker.


# ---------------------------------------------------------------------------
# In-memory S3 fake — a real key/value store so the key IS the test surface.
# ---------------------------------------------------------------------------


class _InMemoryS3:
    """Minimal boto3-S3-shaped fake backed by a dict keyed on the S3 Key.

    The whole point of SEAM-1 is the KEY. A MagicMock would hide key collisions;
    this fake makes two writes to the same key genuinely overwrite each other and
    two writes to different keys genuinely coexist -- exactly the production S3
    semantics the collision proof depends on.
    """

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_keys: list[str] = []
        self.get_keys: list[str] = []

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **_: Any) -> None:
        self.objects[Key] = Body
        self.put_keys.append(Key)

    def get_object(self, *, Bucket: str, Key: str, **_: Any) -> dict[str, Any]:
        self.get_keys.append(Key)
        if Key not in self.objects:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "not found"}}, "GetObject")
        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_object(self, *, Bucket: str, Key: str, **_: Any) -> None:
        self.objects.pop(Key, None)

    def get_paginator(self, _operation: str) -> _FakePaginator:
        """Return a paginator that flat-lists keys under a prefix (no delimiter).

        Mirrors boto3's list_objects_v2 paginate(Prefix=...) contract closely
        enough for the SEAM-1 scan-all purge: it returns ``Contents`` with
        ``Key`` for every stored object whose key starts with the prefix. This
        is what makes ``purge_project_all_entities`` genuinely enumerate every
        v2 entity segment AND the legacy keys -- a MagicMock would hide whether
        the scan actually reaches the v2 keys.
        """
        return _FakePaginator(self)


class _FakePaginator:
    """Minimal boto3 list_objects_v2 paginator over the in-memory store."""

    def __init__(self, fake: _InMemoryS3) -> None:
        self._fake = fake

    def paginate(self, *, Bucket: str, Prefix: str = "", **_: Any) -> list[dict[str, Any]]:
        contents = [{"Key": key} for key in sorted(self._fake.objects) if key.startswith(Prefix)]
        return [{"Contents": contents}]


def _make_storage(fake: _InMemoryS3, *, legacy_fallback_enabled: bool = True) -> S3DataFrameStorage:
    """S3DataFrameStorage wired to the in-memory fake (no network)."""
    orchestrator = RetryOrchestrator(
        policy=DefaultRetryPolicy(RetryPolicyConfig(max_attempts=1, base_delay=0.0, jitter=False)),
        budget=RetryBudget(BudgetConfig(per_subsystem_max=50, global_max=100)),
        circuit_breaker=CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=99, recovery_timeout=60.0, name="seam1-test")
        ),
        subsystem=Subsystem.S3,
    )
    storage = S3DataFrameStorage(
        location=S3LocationConfig(bucket="seam1-bucket", region="us-east-1"),
        prefix="dataframes/",
        retry_orchestrator=orchestrator,
        legacy_fallback_enabled=legacy_fallback_enabled,
    )
    # Bypass real boto3 -- the storage calls self._get_client() once.
    storage._client = fake  # type: ignore[assignment]
    return storage


PROJECT = "1143843662099250"  # the real offer warm target (entity_registry)
_WM = datetime(2026, 6, 8, 12, 0, 0, tzinfo=UTC)


def _offer_frame(rows: int, *, mrr_value: float | None) -> pl.DataFrame:
    """A populated offer frame: ``rows`` active offers with mrr/offer_id."""
    return pl.DataFrame(
        {
            "gid": [f"offer_{i}" for i in range(rows)],
            "section": ["active"] * rows,
            "is_completed": [False] * rows,
            "offer_id": [f"OID-{i}" for i in range(rows)],
            "mrr": [mrr_value] * rows,
        }
    )


def _section_frame(rows: int) -> pl.DataFrame:
    """A section-shaped frame (no economic columns) for the SAME project_gid."""
    return pl.DataFrame(
        {
            "gid": [f"section_row_{i}" for i in range(rows)],
            "section": ["Onboarding"] * rows,
            "status": ["New"] * rows,
        }
    )


# ===========================================================================
# Proof 1 — cross-entity collision (the telos / G-DENOM)
# ===========================================================================


class TestCrossEntityCollision:
    """The 62 must stay 62 after a section warm of the same project GID."""

    async def test_section_write_does_not_clobber_offer_frame_v2(self) -> None:
        """SEAM-1 GREEN: offer (62) survives a section warm of the same project.

        Write the healthy offer frame under entity 'offer', then write a section
        frame under entity 'section' to the SAME project_gid. With the entity key
        they land on DIFFERENT S3 keys, so the offer read still returns 62 rows.
        """
        fake = _InMemoryS3()
        storage = _make_storage(fake)

        # 1. Healthy offer warm: 62 active offers.
        offer_df = _offer_frame(62, mrr_value=1282.0)
        assert await storage.save_dataframe(PROJECT, offer_df, _WM, entity_type="offer")

        # 2. Section warm of the SAME project clobbers... or does it?
        section_df = _section_frame(7)
        assert await storage.save_dataframe(PROJECT, section_df, _WM, entity_type="section")

        # 3. Re-read the offer frame. THE TELOS: still 62.
        loaded_offer, _wm = await storage.load_dataframe(PROJECT, entity_type="offer")
        assert loaded_offer is not None
        assert len(loaded_offer) == 62, (
            f"G-DENOM VIOLATED: offer frame clobbered to {len(loaded_offer)} rows "
            "by a section warm of the same project GID"
        )

        # And the section frame is independently readable (7 rows).
        loaded_section, _ = await storage.load_dataframe(PROJECT, entity_type="section")
        assert loaded_section is not None
        assert len(loaded_section) == 7

        # The two frames live at DIFFERENT keys (the mechanism).
        assert storage._df_key(PROJECT, "offer") != storage._df_key(PROJECT, "section")
        assert storage._df_key(PROJECT, "offer") in fake.objects
        assert storage._df_key(PROJECT, "section") in fake.objects

    async def test_broken_entity_agnostic_key_DOES_clobber(self) -> None:
        """DELIBERATELY-BROKEN: the entity-AGNOSTIC key reproduces the clobber.

        This is the RED proof that the entity-key is what prevents the collision.
        Writing BOTH frames with entity_type=None routes them to the SAME legacy
        key dataframes/{gid}/dataframe.parquet -- the section write overwrites the
        offer frame, collapsing 62 -> 7. If this test ever STOPPED clobbering, the
        defect would be un-falsifiable and the GREEN test above would be theater.
        """
        fake = _InMemoryS3()
        storage = _make_storage(fake)

        # Both writes omit entity_type -> both hit the legacy entity-agnostic key.
        offer_df = _offer_frame(62, mrr_value=1282.0)
        assert await storage.save_dataframe(PROJECT, offer_df, _WM, entity_type=None)
        section_df = _section_frame(7)
        assert await storage.save_dataframe(PROJECT, section_df, _WM, entity_type=None)

        # The legacy read now returns the SECTION frame (7), not the offer (62).
        loaded, _ = await storage.load_dataframe(PROJECT, entity_type=None)
        assert loaded is not None
        assert len(loaded) == 7, (
            "Expected the entity-agnostic key to clobber 62 -> 7. If this is no "
            "longer 7, the collision is un-reproducible and the v2 proof is theater."
        )
        # Both writes targeted the identical key (the root cause).
        assert storage._df_key(PROJECT, None) == "dataframes/1143843662099250/dataframe.parquet"

    async def test_dual_read_fallback_preserves_live_legacy_frame(self) -> None:
        """Decision 2B: a v2 read MISS falls back to the legacy frame (no cold window).

        Simulates the migration window: the live 62 is still at the legacy key
        (no v2 offer warm has happened yet). An offer read (entity_type='offer')
        misses v2 and falls back to legacy, returning the 62 with ZERO cold window.
        """
        fake = _InMemoryS3()
        storage = _make_storage(fake, legacy_fallback_enabled=True)

        # Pre-migration: the 62 lives ONLY at the legacy entity-agnostic key.
        offer_df = _offer_frame(62, mrr_value=1282.0)
        assert await storage.save_dataframe(PROJECT, offer_df, _WM, entity_type=None)
        assert storage._df_key(PROJECT, "offer") not in fake.objects  # no v2 yet

        # Offer read: v2 miss -> legacy fallback -> 62 preserved.
        loaded, _ = await storage.load_dataframe(PROJECT, entity_type="offer")
        assert loaded is not None
        assert len(loaded) == 62

    async def test_dual_read_fallback_disabled_returns_none_on_v2_miss(self) -> None:
        """Post-migration: with fallback OFF, a v2 miss does NOT read legacy."""
        fake = _InMemoryS3()
        storage = _make_storage(fake, legacy_fallback_enabled=False)

        await storage.save_dataframe(
            PROJECT, _offer_frame(62, mrr_value=1.0), _WM, entity_type=None
        )
        loaded, _ = await storage.load_dataframe(PROJECT, entity_type="offer")
        assert loaded is None  # fallback disabled -> legacy not consulted

    async def test_v2_takes_precedence_over_legacy(self) -> None:
        """Once a v2 offer warm lands, the v2 frame wins over the stale legacy one."""
        fake = _InMemoryS3()
        storage = _make_storage(fake)

        # Stale legacy frame (7) + fresh v2 offer frame (62).
        await storage.save_dataframe(PROJECT, _section_frame(7), _WM, entity_type=None)
        await storage.save_dataframe(
            PROJECT, _offer_frame(62, mrr_value=1282.0), _WM, entity_type="offer"
        )

        loaded, _ = await storage.load_dataframe(PROJECT, entity_type="offer")
        assert loaded is not None
        assert len(loaded) == 62  # v2 wins; legacy is not consulted on a v2 hit

    async def test_section_key_is_collision_free(self) -> None:
        """The section-arm of the collision: per-entity section parquet keys differ."""
        fake = _InMemoryS3()
        storage = _make_storage(fake)

        await storage.save_section(
            PROJECT, "sec_1", _offer_frame(3, mrr_value=1.0), entity_type="offer"
        )
        await storage.save_section(PROJECT, "sec_1", _section_frame(9), entity_type="section")

        offer_sec = await storage.load_section(PROJECT, "sec_1", entity_type="offer")
        section_sec = await storage.load_section(PROJECT, "sec_1", entity_type="section")
        assert offer_sec is not None and len(offer_sec) == 3
        assert section_sec is not None and len(section_sec) == 9
        assert storage._section_key(PROJECT, "sec_1", "offer") != storage._section_key(
            PROJECT, "sec_1", "section"
        )


# ===========================================================================
# Proof 1b — scan-all purge reaches the v2 frame (D-1b, G-PROPAGATE)
# ===========================================================================


class TestScanAllPurge:
    """The project-targeted purge must reach EVERY layout, not just legacy.

    D-1b: the invalidate Lambda has no entity_type in scope, so it must scan-all
    delete across dataframes/{gid}/*/ . An entity-agnostic-only delete leaves the
    v2 frame orphaned -> force-rebuild silently no-ops (operator stale-serve
    footgun). The deliberately-broken companion proves the orphan.
    """

    async def test_purge_all_entities_deletes_v2_and_legacy(self) -> None:
        """GREEN: scan-all purge removes the v2 entity frame AND the legacy keys."""
        fake = _InMemoryS3()
        storage = _make_storage(fake)

        # A v2 offer frame + a v2 section, and a stale legacy frame, all under P.
        await storage.save_dataframe(
            PROJECT, _offer_frame(62, mrr_value=1282.0), _WM, entity_type="offer"
        )
        await storage.save_section(PROJECT, "sec_1", _section_frame(9), entity_type="section")
        await storage.save_dataframe(PROJECT, _section_frame(7), _WM, entity_type=None)

        # Sanity: all three layouts are present under the project prefix.
        assert storage._df_key(PROJECT, "offer") in fake.objects
        assert storage._section_key(PROJECT, "sec_1", "section") in fake.objects
        assert storage._df_key(PROJECT, None) in fake.objects

        deleted = await storage.purge_project_all_entities(PROJECT)

        # Every object under dataframes/{PROJECT}/ is gone (all layouts).
        assert deleted >= 3
        remaining = [k for k in fake.objects if k.startswith(f"dataframes/{PROJECT}/")]
        assert remaining == [], f"scan-all purge left orphans: {remaining}"
        # Specifically: the v2 offer frame the entity-agnostic delete would miss.
        assert storage._df_key(PROJECT, "offer") not in fake.objects
        assert storage._section_key(PROJECT, "sec_1", "section") not in fake.objects

    async def test_broken_entity_agnostic_delete_ORPHANS_v2_frame(self) -> None:
        """DELIBERATELY-BROKEN: the legacy-only delete leaves the v2 frame alive.

        This is the RED proof of D-1b. ``delete_dataframe(P)`` with no
        entity_type purges only the legacy key; the live v2 offer frame survives
        -> the force-rebuild silently no-ops. If this ever STOPPED orphaning, the
        scan-all proof above would be theater.
        """
        fake = _InMemoryS3()
        storage = _make_storage(fake)

        # Live v2 offer frame (the denominator) + a stale legacy frame.
        await storage.save_dataframe(
            PROJECT, _offer_frame(62, mrr_value=1282.0), _WM, entity_type="offer"
        )
        await storage.save_dataframe(PROJECT, _section_frame(7), _WM, entity_type=None)

        # The OLD (broken) purge path: entity-agnostic delete only.
        await storage.delete_dataframe(PROJECT)  # entity_type omitted

        # The v2 offer frame is ORPHANED -- the bug.
        assert storage._df_key(PROJECT, "offer") in fake.objects, (
            "Expected the entity-agnostic delete to ORPHAN the v2 frame. If it is "
            "gone, the D-1b defect is un-falsifiable and the scan-all proof is theater."
        )
        loaded, _ = await storage.load_dataframe(PROJECT, entity_type="offer")
        assert loaded is not None and len(loaded) == 62  # stale frame still served

    async def test_purge_is_idempotent_on_empty_project(self) -> None:
        """Scan-all purge of a project with no objects returns 0 (idempotent)."""
        fake = _InMemoryS3()
        storage = _make_storage(fake)
        assert await storage.purge_project_all_entities("0000") == 0

    async def test_purge_prefix_does_not_match_sibling_project(self) -> None:
        """The trailing-slash prefix must not purge a GID-prefixed sibling.

        Project '11' must NOT be purged when invalidating project '1' (a naive
        prefix match would catch dataframes/11/... under dataframes/1).
        """
        fake = _InMemoryS3()
        storage = _make_storage(fake)

        await storage.save_dataframe("1", _offer_frame(2, mrr_value=1.0), _WM, entity_type="offer")
        await storage.save_dataframe("11", _offer_frame(5, mrr_value=1.0), _WM, entity_type="offer")

        await storage.purge_project_all_entities("1")

        # Sibling "11" survives.
        assert [k for k in fake.objects if k.startswith("dataframes/1/")] == []
        assert storage._df_key("11", "offer") in fake.objects


class TestLambdaInvalidateScanAll:
    """The invalidate Lambda must purge the v2 frame end-to-end (D-1b)."""

    async def test_invalidate_project_purges_v2_frame(self) -> None:
        """End-to-end: handler_async(invalidate_project=...) removes the v2 frame.

        Wires a real S3DataFrameStorage (in-memory fake) through
        create_section_persistence so the Lambda's scan-all purge is exercised
        against genuine v2 keys -- not a mock that would mask the orphan.
        """
        from unittest.mock import patch

        from autom8_asana.dataframes import section_persistence as sp
        from autom8_asana.lambda_handlers import cache_invalidate as ci

        fake = _InMemoryS3()
        storage = _make_storage(fake)

        # Seed the live v2 offer frame + a v2 section under the project.
        await storage.save_dataframe(
            PROJECT, _offer_frame(62, mrr_value=1282.0), _WM, entity_type="offer"
        )
        await storage.save_section(PROJECT, "sec_1", _section_frame(9), entity_type="offer")
        assert storage._df_key(PROJECT, "offer") in fake.objects

        persistence = sp.create_section_persistence(storage=storage)

        # The Lambda imports create_section_persistence lazily from its source
        # module; patch it there so the in-memory storage flows through.
        with (
            patch.object(sp, "create_section_persistence", return_value=persistence),
            patch.object(ci, "emit_metric"),
        ):
            result = await ci.handler_async(
                {"clear_tasks": False, "invalidate_project": PROJECT},
                context=None,
            )

        assert result["statusCode"] == 200
        assert result["body"]["projects_invalidated"] == 1
        # THE PROOF: the v2 offer frame the old legacy-only delete would orphan
        # is gone after the Lambda runs.
        assert storage._df_key(PROJECT, "offer") not in fake.objects
        assert storage._section_key(PROJECT, "sec_1", "offer") not in fake.objects
        assert [k for k in fake.objects if k.startswith(f"dataframes/{PROJECT}/")] == []


# ===========================================================================
# Proof 2 — present-but-null value-population receipt (FM-4)
# ===========================================================================


class TestPopulationReceipt:
    """A present-but-null economics frame must fire RED."""

    def test_present_but_null_mrr_fires_below_floor(self) -> None:
        """RED: 62 active offers with all-null mrr -> below_floor receipt."""
        df = _offer_frame(62, mrr_value=None)  # present rows, null economics
        receipt = post_build_population_receipt(
            merged_df=df, schema=OFFER_SCHEMA, entity_type="offer", project_gid=PROJECT
        )
        assert receipt.assessed is True
        assert receipt.active_rows == 62
        assert receipt.below_floor is True, (
            "FM-4 VIOLATED: a present-but-null mrr frame did not fire the receipt"
        )
        assert receipt.column_nonnull_rates["mrr"] == 0.0

    def test_fully_populated_frame_does_not_fire(self) -> None:
        """GREEN: a fully-populated frame clears the floor."""
        df = _offer_frame(62, mrr_value=1282.0)
        receipt = post_build_population_receipt(
            merged_df=df, schema=OFFER_SCHEMA, entity_type="offer", project_gid=PROJECT
        )
        assert receipt.assessed is True
        assert receipt.below_floor is False
        assert receipt.min_rate >= POPULATION_WARN_THRESHOLD
        assert receipt.column_nonnull_rates["mrr"] == 1.0
        assert receipt.column_nonnull_rates["offer_id"] == 1.0

    def test_partial_null_below_threshold_fires(self) -> None:
        """RED: 50% mrr-populated active subset (< 0.80) fires below_floor."""
        df = pl.DataFrame(
            {
                "gid": [f"o{i}" for i in range(10)],
                "section": ["active"] * 10,
                "is_completed": [False] * 10,
                "offer_id": [f"OID-{i}" for i in range(10)],
                "mrr": [100.0 if i < 5 else None for i in range(10)],  # 50% populated
            }
        )
        receipt = post_build_population_receipt(
            merged_df=df, schema=OFFER_SCHEMA, entity_type="offer", project_gid=PROJECT
        )
        assert receipt.below_floor is True
        assert receipt.column_nonnull_rates["mrr"] == 0.5

    def test_inactive_rows_excluded_from_subset(self) -> None:
        """The receipt scopes to ACTIVE/ACTIVATING -- inactive nulls don't count.

        62 active rows fully populated + 40 inactive rows with null mrr. Because
        the receipt assesses only the active subset, the rate is 1.0 (GREEN). If
        it (wrongly) assessed the whole frame, the rate would be 62/102 < floor.
        """
        active = _offer_frame(62, mrr_value=1282.0)
        inactive = pl.DataFrame(
            {
                "gid": [f"inact_{i}" for i in range(40)],
                "section": ["inactive"] * 40,
                "is_completed": [False] * 40,
                "offer_id": [f"OID-x{i}" for i in range(40)],
                "mrr": [None] * 40,
            }
        )
        df = pl.concat([active, inactive], how="diagonal_relaxed")
        receipt = post_build_population_receipt(
            merged_df=df, schema=OFFER_SCHEMA, entity_type="offer", project_gid=PROJECT
        )
        assert receipt.active_rows == 62
        assert receipt.below_floor is False
        assert receipt.column_nonnull_rates["mrr"] == 1.0

    def test_completed_rows_excluded_from_active_subset(self) -> None:
        """is_completed=True is a terminal override -> not in the active subset."""
        df = pl.DataFrame(
            {
                "gid": [f"o{i}" for i in range(10)],
                "section": ["active"] * 10,
                "is_completed": [i >= 5 for i in range(10)],  # last 5 completed
                "offer_id": [f"OID-{i}" for i in range(10)],
                "mrr": [100.0] * 10,
            }
        )
        receipt = post_build_population_receipt(
            merged_df=df, schema=OFFER_SCHEMA, entity_type="offer", project_gid=PROJECT
        )
        assert receipt.active_rows == 5  # only the 5 non-completed active rows

    def test_non_value_entity_skips(self) -> None:
        """section/project (no value columns) are a safe no-op."""
        from autom8_asana.dataframes.schemas.section import SECTION_SCHEMA

        df = _section_frame(20)
        receipt = post_build_population_receipt(
            merged_df=df, schema=SECTION_SCHEMA, entity_type="section", project_gid=PROJECT
        )
        assert receipt.assessed is False
        assert receipt.below_floor is False

    def test_receipt_never_raises_on_malformed_frame(self) -> None:
        """WARN-first: a frame missing the section column degrades, never raises."""
        df = pl.DataFrame({"gid": ["a"], "mrr": [None], "offer_id": ["x"]})  # no 'section'
        receipt = post_build_population_receipt(
            merged_df=df, schema=OFFER_SCHEMA, entity_type="offer", project_gid=PROJECT
        )
        # No classifiable active subset -> skipped, not an exception.
        assert receipt.assessed is False


# ===========================================================================
# Proof 3 — FM-2 status extraction (cf:Status)
# ===========================================================================


class TestStatusExtraction:
    """status populates from cf:Status (was 100% null under source=None)."""

    def test_section_schema_status_sourced_from_cf(self) -> None:
        """The schema declaration now points status at the Status custom field."""
        from autom8_asana.dataframes.schemas.section import SECTION_SCHEMA

        col = SECTION_SCHEMA.get_column("status")
        assert col is not None
        assert col.source == "cf:Status", (
            "FM-2 VIOLATED: section status source is not cf:Status (source=None "
            "dispatches to a nonexistent _extract_status -> 100% null)"
        )

    def test_project_schema_status_sourced_from_cf(self) -> None:
        from autom8_asana.dataframes.schemas.project import PROJECT_SCHEMA

        col = PROJECT_SCHEMA.get_column("status")
        assert col is not None
        assert col.source == "cf:Status"

    def test_status_extracts_non_null_from_task_with_status_cf(self) -> None:
        """RED->GREEN: a task carrying a Status custom field yields a non-null status.

        Builds the generic SchemaExtractor (the extractor section/project bind)
        over the section schema and a stub resolver that returns the Status cf
        value. Under the OLD source=None this returned None (100% null); under
        cf:Status it returns the field value.
        """
        from autom8_asana.dataframes.extractors.schema import SchemaExtractor
        from autom8_asana.dataframes.schemas.section import SECTION_SCHEMA

        class _StubResolver:
            """Returns the Status cf value via the cf: path used by all cf columns."""

            def get_value(self, task: Any, source: str, column_def: Any = None) -> Any:
                # Mirrors DefaultCustomFieldResolver: strip cf: and look up by name.
                name = source[3:] if source.startswith("cf:") else source
                return getattr(task, "_cf", {}).get(name)

        class _StubTask:
            gid = "task_1"
            name = "Acme Co"
            resource_subtype = "default_task"
            created_at = "2026-06-08T00:00:00Z"
            modified_at = "2026-06-08T00:00:00Z"
            due_on = None
            completed = False
            completed_at = None
            parent = None
            tags: list[Any] = []
            _cf = {"Status": "Live"}

        extractor = SchemaExtractor(SECTION_SCHEMA, resolver=_StubResolver())
        row = extractor.extract(_StubTask())  # type: ignore[arg-type]
        # TaskRow exposes columns as attributes; status must be the cf value.
        status = getattr(row, "status", None)
        if status is None and hasattr(row, "model_dump"):
            status = row.model_dump().get("status")
        if status is None and isinstance(row, dict):
            status = row.get("status")
        assert status == "Live", (
            f"FM-2 VIOLATED: status extracted as {status!r}, expected 'Live' from "
            "the cf:Status path"
        )


# ===========================================================================
# Proof 4 — F-1 reader threading: the honest-empty probe reads the v2 manifest
# ===========================================================================


class TestHonestEmptyProbeReadsV2Manifest:
    """F-1a behavioral RED partner to the NFR-2 inventory guard.

    ``UniversalResolutionStrategy._honest_empty_frame_if_complete`` reads the
    SectionManifest to decide honest-empty-200 vs build-on-miss-503. F-1a: it
    must thread ``self.entity_type`` so it reads the v2 entity-keyed manifest.
    Behavioral proof: a manifest that lives ONLY at the v2 'offer' key is found
    by the threaded read (-> honest-empty frame), whereas an entity_type-less
    read would miss it (no legacy manifest) and return None (503).
    """

    async def test_probe_finds_v2_only_manifest(self) -> None:
        """GREEN: a v2-only (no legacy) honest-complete manifest yields an empty frame.

        Under the OLD entity-agnostic read, get_manifest_async(project_gid) would
        consult the legacy key, find nothing, and return None (503). The threaded
        read consults the v2 'offer' key, finds the vacuously-honest-complete
        manifest, and returns an empty schema'd frame (honest-empty-200).
        """
        from unittest.mock import patch

        from autom8_asana.dataframes import section_persistence as sp
        from autom8_asana.services.dynamic_index import DynamicIndexCache
        from autom8_asana.services.universal_strategy import UniversalResolutionStrategy

        fake = _InMemoryS3()
        storage = _make_storage(fake)
        persistence = sp.create_section_persistence(storage=storage)

        # Manifest at the v2 'offer' key ONLY (empty sections -> vacuously
        # honest-complete per is_honest_complete). No legacy manifest exists.
        async with persistence:
            await persistence.create_manifest_async(PROJECT, entity_type="offer", section_gids=[])
        assert storage._manifest_key(PROJECT, "offer") in fake.objects
        assert storage._manifest_key(PROJECT, None) not in fake.objects  # no legacy

        # Clear the warm process-local manifest cache create_manifest_async
        # populated, so the probe MUST issue a real S3 GET -- making the v2 key
        # the observable read surface (otherwise the cache would mask the key).
        persistence._manifest_cache.clear()
        fake.get_keys.clear()

        strategy = UniversalResolutionStrategy(entity_type="offer", index_cache=DynamicIndexCache())

        # The probe constructs its own persistence via the module factory; patch
        # it to flow the in-memory storage through (mirrors the Lambda test).
        with patch.object(sp, "create_section_persistence", return_value=persistence):
            frame = await strategy._honest_empty_frame_if_complete(PROJECT)

        assert frame is not None, (
            "F-1a VIOLATED: the honest-empty probe did not find the v2-only "
            "manifest -- an entity_type-less read consulted the legacy key (None) "
            "and returned a false 503 for an honest-complete project."
        )
        assert frame.height == 0  # honest-EMPTY frame

        # The mechanism: the v2 entity-keyed manifest key was read.
        assert any(k == storage._manifest_key(PROJECT, "offer") for k in fake.get_keys), (
            "expected a GET against the v2 'offer' manifest key"
        )

    async def test_probe_returns_none_when_no_v2_manifest(self) -> None:
        """Control: with no manifest at the v2 key, the probe returns None (503).

        Pins the discriminating power of the GREEN test above: the empty frame is
        returned BECAUSE the v2 manifest exists, not unconditionally.
        """
        from unittest.mock import patch

        from autom8_asana.dataframes import section_persistence as sp
        from autom8_asana.services.dynamic_index import DynamicIndexCache
        from autom8_asana.services.universal_strategy import UniversalResolutionStrategy

        fake = _InMemoryS3()
        storage = _make_storage(fake)
        persistence = sp.create_section_persistence(storage=storage)

        strategy = UniversalResolutionStrategy(entity_type="offer", index_cache=DynamicIndexCache())
        with patch.object(sp, "create_section_persistence", return_value=persistence):
            frame = await strategy._honest_empty_frame_if_complete(PROJECT)

        assert frame is None  # no manifest -> build-on-miss 503, never a false empty
