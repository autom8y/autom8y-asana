"""Behavioral guard: the offline loader reads the ENTITY-keyed frame, not the fossil.

Consumer-0 (the offline ``metrics`` CLI reader) was the 3rd locus of the
entity-blind-reader class. ``python -m autom8_asana.metrics active_mrr`` must
return the entity-correct, populated active set (~$79,485 banked) -- never the
silent legacy fossil (~$8,775, 99.8% null) that lives at the entity-AGNOSTIC
``dataframes/{gid}/sections/`` prefix.

PR #111 (7fa56d19, "SEAM-1 entity-identity in the S3 key + read") landed the
loader rebind: ``load_project_dataframe`` grew an ``entity_type`` parameter and
``metrics/__main__.py`` threads ``metric.scope.entity_type`` into it
(``read_entity_type = args.entity_type or metric.scope.entity_type``). The
``test_seam1_callsite_inventory`` AST guard proves -- STRUCTURALLY -- that every
substrate call-site threads ``entity_type``.

What was MISSING is a BEHAVIORAL guard at the loader's S3-prefix semantics: a
test where the legacy fossil and the entity-keyed v2 frame COEXIST under one
project, asserting the entity-aware read returns ONLY the v2 frame and the
fossil's value can never contaminate the answer. The AST guard would still pass
if the loader's prefix-resolution logic regressed (e.g. ``entity_type`` accepted
but ignored, or the v2/legacy branch inverted) -- it checks the call graph, not
the bytes that come back. This file closes that gap.

DENOMINATOR (G-DENOM): the entity-aware read of ``active_mrr``'s scope
(``entity_type="offer"``) returns the populated entity-keyed active set, NOT the
fossil. The fossil sum ($8,775) and the healthy sum ($79,485) are deliberately
DISTINCT and NON-OVERLAPPING so the assertion is unambiguous.

MUTATION PROOF (G-THEATER): ``test_legacy_scan_all_read_IS_fossil_contaminated``
exercises the legacy ``entity_type=None`` scan-all path against the SAME fixture
and asserts it DOES concatenate the fossil (sum = fossil + healthy). That is the
broken-fixture-RED control: it proves the fixture genuinely carries a fossil that
a non-entity-aware read would pick up, so the entity-aware PASS is meaningful and
not vacuous. If the entity-aware read ever regressed to the fossil prefix, its
assertion would collapse to $8,775 and FAIL.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import polars as pl

from autom8_asana.dataframes.offline import load_project_dataframe
from autom8_asana.metrics.registry import MetricRegistry

# The canonical legacy-root project GID from the entity-blind-reader receipt.
_PROJECT_GID = "1143843662099250"

# Two coexisting frames under ONE project, with DISTINCT, non-overlapping sums.
#   Legacy fossil  (dataframes/{gid}/sections/)       -> mrr sums to 8_775.0
#   Entity v2 frame (dataframes/{gid}/offer/sections/) -> mrr sums to 79_485.0
_FOSSIL_PREFIX = f"dataframes/{_PROJECT_GID}/sections/"
_OFFER_V2_PREFIX = f"dataframes/{_PROJECT_GID}/offer/sections/"

_FOSSIL_SUM = 8_775.0
_HEALTHY_SUM = 79_485.0

# Section parquet contents. The fossil's single section sums to $8,775; the
# entity-keyed v2 frame's single section sums to $79,485. Distinct values let an
# assertion on the returned sum pinpoint EXACTLY which prefix was read.
_FOSSIL_KEY = f"{_FOSSIL_PREFIX}ACTIVE.parquet"
_OFFER_V2_KEY = f"{_OFFER_V2_PREFIX}ACTIVE.parquet"

_FOSSIL_DF = pl.DataFrame({"name": ["fossil-row"], "section": ["ACTIVE"], "mrr": [_FOSSIL_SUM]})
_OFFER_V2_DF = pl.DataFrame({"name": ["offer-row"], "section": ["ACTIVE"], "mrr": [_HEALTHY_SUM]})


def _parquet_bytes(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.write_parquet(buf)
    buf.seek(0)
    return buf.read()


def _coexisting_frames_client() -> MagicMock:
    """A mock S3 client serving BOTH the fossil and the entity-keyed v2 frame.

    The paginator answers ``list_objects_v2`` per ``Prefix``:
      * the bare legacy prefix lists ONLY the fossil key,
      * the ``/offer/`` v2 prefix lists ONLY the v2 key,
      * the whole-project prefix (scan-all) lists BOTH.
    ``get_object`` returns the parquet bytes matching the requested key. This
    mirrors the real S3 layout where a project carries a stale entity-agnostic
    root AND a populated entity-segmented frame simultaneously.
    """
    client = MagicMock()
    paginator = MagicMock()
    client.get_paginator.return_value = paginator

    def paginate(*, Bucket: str, Prefix: str) -> list[dict]:  # noqa: N803 (boto3 kwarg)
        contents: list[dict] = []
        if Prefix == _OFFER_V2_PREFIX:
            contents = [{"Key": _OFFER_V2_KEY}]
        elif Prefix == _FOSSIL_PREFIX:
            contents = [{"Key": _FOSSIL_KEY}]
        elif Prefix == f"dataframes/{_PROJECT_GID}/":
            # scan-all: the whole project prefix surfaces BOTH frames.
            contents = [{"Key": _FOSSIL_KEY}, {"Key": _OFFER_V2_KEY}]
        return [{"Contents": contents}]

    paginator.paginate.side_effect = paginate

    def get_object(*, Bucket: str, Key: str) -> dict:  # noqa: N803 (boto3 kwarg)
        body = MagicMock()
        body.read.return_value = _parquet_bytes(
            _OFFER_V2_DF if Key == _OFFER_V2_KEY else _FOSSIL_DF
        )
        return {"Body": body}

    client.get_object.side_effect = get_object
    return client


class TestEntityAwareReadExcludesFossil:
    """The loader's entity_type read selects the v2 frame, never the fossil."""

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_entity_aware_read_returns_healthy_set_not_fossil(self, mock_boto3: MagicMock) -> None:
        """entity_type='offer' reads dataframes/{gid}/offer/sections/ -> $79,485.

        G-DENOM: the active set is the entity-keyed populated frame. The fossil
        ($8,775) is at the bare legacy prefix and MUST NOT appear in the result.
        If the loader regressed to the fossil prefix, this sum would be $8,775.
        """
        mock_boto3.client.return_value = _coexisting_frames_client()

        df = load_project_dataframe(_PROJECT_GID, bucket="test-bucket", entity_type="offer")

        assert df["mrr"].sum() == _HEALTHY_SUM, (
            "ENTITY-BLIND REGRESSION: entity_type='offer' read did NOT return the "
            f"entity-keyed v2 frame (${_HEALTHY_SUM:,.0f}); got "
            f"${df['mrr'].sum():,.0f}. If this equals the fossil ${_FOSSIL_SUM:,.0f}, "
            "the loader is reading the legacy entity-AGNOSTIC prefix again "
            "(Consumer-0 the entity-blind reader)."
        )
        # The fossil's sentinel value never appears -- the fossil row is excluded.
        assert _FOSSIL_SUM not in set(df["mrr"].to_list())
        assert df["name"].to_list() == ["offer-row"]

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_active_mrr_scope_drives_entity_aware_read(self, mock_boto3: MagicMock) -> None:
        """The REAL active_mrr metric scope (entity_type='offer') reads the v2 frame.

        Grounds the guard in the actual metric the CLI computes: the metrics CLI
        threads ``metric.scope.entity_type`` into the loader. Reading that scope
        from the live registry (not a hardcoded literal) proves the scope the CLI
        passes resolves to the populated entity frame, not the fossil.
        """
        mock_boto3.client.return_value = _coexisting_frames_client()

        scope_entity_type = MetricRegistry().get_metric("active_mrr").scope.entity_type
        assert scope_entity_type == "offer"

        df = load_project_dataframe(
            _PROJECT_GID, bucket="test-bucket", entity_type=scope_entity_type
        )
        assert df["mrr"].sum() == _HEALTHY_SUM

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_legacy_scan_all_read_IS_fossil_contaminated(self, mock_boto3: MagicMock) -> None:
        """BROKEN-FIXTURE-RED control: entity_type=None scan-all DOES eat the fossil.

        This is the mutation/discrimination proof. The legacy reader semantics
        (no entity_type -> scan-all) concatenate the bare-legacy fossil AND the
        v2 frame, so the sum is contaminated ($8,775 + $79,485). This proves:
          1. the fixture genuinely carries a fossil a non-entity-aware read picks
             up (the entity-aware PASS above is therefore meaningful, not vacuous),
          2. the loader's entity_type parameter is load-bearing -- omitting it
             changes the answer.
        If this assertion ever returned only $79,485, the fixture would no longer
        contain a fossil and the entity-aware test would be theater.
        """
        mock_boto3.client.return_value = _coexisting_frames_client()

        df = load_project_dataframe(_PROJECT_GID, bucket="test-bucket", entity_type=None)

        assert df["mrr"].sum() == _FOSSIL_SUM + _HEALTHY_SUM, (
            "FIXTURE INVALID: the scan-all (entity_type=None) read should "
            f"concatenate the fossil (${_FOSSIL_SUM:,.0f}) AND the v2 frame "
            f"(${_HEALTHY_SUM:,.0f}). Got ${df['mrr'].sum():,.0f}. Without a "
            "fossil-contaminated control, the entity-aware test proves nothing."
        )
        # Both frames present in the scan-all read -> the fossil IS reachable.
        assert _FOSSIL_SUM in set(df["mrr"].to_list())
        assert _HEALTHY_SUM in set(df["mrr"].to_list())

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_entity_aware_falls_back_to_legacy_only_on_v2_miss(self, mock_boto3: MagicMock) -> None:
        """The sanctioned legacy fallback fires ONLY when the v2 prefix is empty.

        SEAM-1 design: entity_type-given reads are v2-first with a legacy fallback
        on MISS. When the v2 frame is absent (a project not yet re-derived under
        the entity layout), the read falls back to the legacy prefix rather than
        raising. This guards that the fallback is a genuine miss-trigger, not an
        always-on path that would silently re-admit the fossil when v2 exists.
        """
        client = MagicMock()
        paginator = MagicMock()
        client.get_paginator.return_value = paginator

        def paginate(*, Bucket: str, Prefix: str) -> list[dict]:  # noqa: N803
            if Prefix == _OFFER_V2_PREFIX:
                return [{"Contents": []}]  # v2 MISS -> triggers legacy fallback
            if Prefix == _FOSSIL_PREFIX:
                return [{"Contents": [{"Key": _FOSSIL_KEY}]}]
            return [{"Contents": []}]

        paginator.paginate.side_effect = paginate

        def get_object(*, Bucket: str, Key: str) -> dict:  # noqa: N803
            body = MagicMock()
            body.read.return_value = _parquet_bytes(_FOSSIL_DF)
            return {"Body": body}

        client.get_object.side_effect = get_object
        mock_boto3.client.return_value = client

        df = load_project_dataframe(_PROJECT_GID, bucket="test-bucket", entity_type="offer")
        # v2 was empty -> fell back to legacy -> the legacy frame is returned.
        assert df["mrr"].sum() == _FOSSIL_SUM
