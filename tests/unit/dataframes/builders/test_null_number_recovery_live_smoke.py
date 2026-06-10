"""LIVE read-only smoke test for the FPC Phase-2 durable cold-read cure.

Invokes the cure's OWN cold-read path (`_read_task_cache_object` and
`_cold_read_durable`) against REAL S3 for a known-populated unit gid and asserts
the recovered task dict yields ``get_custom_field_value(..., "MRR") == 1500``.

This is the proof the two prior cures lacked: it reads the ACTUAL live object at
``asana-cache/tasks/1207519540893045/task.json`` through the cure's REAL boto3 GET
+ REAL json parsing + REAL envelope unwrap — not a stub.

READ-ONLY: a single boto3 ``get_object`` (+ optional ``.gz`` fallback). NEVER writes
S3, NEVER mutates anything, NEVER charges an Asana GET (S3 is durable cache).

SKIPPED in CI (no AWS creds): gated on a real ``ASANA_CACHE_S3_BUCKET`` env + a
``--run-live-smoke``-equivalent env flag, so the unit suite stays hermetic. RUN
locally with creds:

    AWS_PROFILE=... ASANA_CACHE_S3_BUCKET=autom8-s3 \
      uv run python -m pytest <thisfile> -o addopts="" -o asyncio_mode=auto \
      -p no:cacheprovider -q
"""

from __future__ import annotations

import os

import pytest

import autom8_asana.dataframes.builders.null_number_recovery as nnr
from autom8_asana.dataframes.views.cf_utils import get_custom_field_value

# A known live-populated Active unit (verified by the provenance probe): its durable
# per-task copy at asana-cache/tasks/1207519540893045/task.json carries MRR 1500.
_LIVE_GID = "1207519540893045"
_EXPECTED_MRR = 1500

# CI hermeticity gate: only run when real S3 creds + bucket are present. Absent
# either, the live read is skipped (CI green) without weakening the local proof.
_HAS_LIVE_S3 = bool(os.environ.get("ASANA_CACHE_S3_BUCKET")) and (
    bool(os.environ.get("AWS_PROFILE"))
    or bool(os.environ.get("AWS_ACCESS_KEY_ID"))
    or os.path.exists(os.path.expanduser("~/.aws/credentials"))
)

pytestmark = pytest.mark.skipif(
    not _HAS_LIVE_S3,
    reason="live S3 smoke read requires ASANA_CACHE_S3_BUCKET + AWS creds (skipped in CI)",
)


def test_live_cold_read_recovers_mrr_1500_through_cure_path():
    """The cure's OWN _read_task_cache_object reads the REAL live object -> MRR 1500."""
    # Reset the module-cached client so this run builds a fresh REAL boto3 client
    # (no test installed a fake before us in this process).
    nnr._S3_CLIENT = None
    nnr._S3_CLIENT_BUILD_ATTEMPTED = False

    client = nnr._get_s3_client()
    assert client is not None, "live boto3 S3 client must be resolvable with creds present"

    from autom8_asana.settings import get_settings

    bucket = get_settings().s3.bucket
    assert bucket, "ASANA_CACHE_S3_BUCKET must resolve a bucket"

    # Invoke the cure's REAL raw-S3 read for the known-populated gid.
    task_data = nnr._read_task_cache_object(client, bucket, _LIVE_GID)
    assert task_data is not None, (
        f"live durable copy for gid {_LIVE_GID} must be present at "
        f"{nnr._cold_task_cache_key(_LIVE_GID)} (bucket {bucket})"
    )

    # The SAME field extraction the cure uses (cf_utils.get_custom_field_value).
    mrr = get_custom_field_value(task_data, "MRR")
    assert mrr == _EXPECTED_MRR, (
        f"live MRR through the cure's read path must be {_EXPECTED_MRR} (got {mrr})"
    )
    print(
        f"\nLIVE SMOKE: gid {_LIVE_GID} key={nnr._cold_task_cache_key(_LIVE_GID)} "
        f"bucket={bucket} -> MRR={mrr}"
    )


async def test_live_cold_read_durable_batch_recovers_mrr_1500():
    """The full async _cold_read_durable batch path recovers the gid from REAL S3."""
    nnr._S3_CLIENT = None
    nnr._S3_CLIENT_BUILD_ATTEMPTED = False

    # store is unused by the rebuilt cold read (durable copies are a parallel write
    # path, not a read tier of the store) — pass a trivial object.
    result = await nnr._cold_read_durable([_LIVE_GID], store=object())
    task_data = result.get(_LIVE_GID)
    assert task_data is not None, f"batch cold read must recover gid {_LIVE_GID} from live S3"
    mrr = get_custom_field_value(task_data, "MRR")
    assert mrr == _EXPECTED_MRR, f"live batch MRR must be {_EXPECTED_MRR} (got {mrr})"
    print(f"\nLIVE SMOKE (batch): _cold_read_durable([{_LIVE_GID}]) -> MRR={mrr}")
