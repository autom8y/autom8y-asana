"""LIVE read-only smoke for the blessed DurableTaskCacheReader (FP-3 substrate).

Invokes the reader's OWN read path (``read_object`` + ``read_batch``) against REAL
S3 for a known-populated unit gid and asserts the recovered task dict yields
``get_custom_field_value(..., "MRR") == 1500``.

This is the integration-boundary-fidelity Layer-4 forcing function for the
StorageNamespaceContract's blessed reader: it reads the ACTUAL live object at
``{TASK_CACHE.prefix}/tasks/1207519540893045/task.json`` through the reader's REAL
boto3 GET + REAL json parse + REAL envelope unwrap, AND it proves the EXECUTING
principal can read it (an AccessDenied would fail the smoke — the Layer-4 grant
assertion).

READ-ONLY: a single boto3 ``get_object`` (+ optional ``.gz`` fallback). NEVER
writes S3, NEVER mutates anything, NEVER charges an Asana GET (S3 is durable cache).

SKIPPED in CI (no AWS creds): gated on a real ``ASANA_CACHE_S3_BUCKET`` env + AWS
creds, so the unit suite stays hermetic. RUN locally with creds:

    ASANA_CACHE_S3_BUCKET=autom8-s3 \
      uv run python -m pytest <thisfile> -o addopts="" -o asyncio_mode=auto \
      -p no:cacheprovider -s -q
"""

from __future__ import annotations

import os

import pytest

from autom8_asana.cache.durable_task_cache import (
    DurableTaskCacheReader,
    task_cache_key,
)
from autom8_asana.dataframes.views.cf_utils import get_custom_field_value
from autom8_asana.storage_namespace import TASK_CACHE

# A known live-populated Active unit: its durable per-task copy carries MRR 1500.
_LIVE_GID = "1207519540893045"
_EXPECTED_MRR = 1500

_HAS_LIVE_S3 = bool(os.environ.get("ASANA_CACHE_S3_BUCKET")) and (
    bool(os.environ.get("AWS_PROFILE"))
    or bool(os.environ.get("AWS_ACCESS_KEY_ID"))
    or os.path.exists(os.path.expanduser("~/.aws/credentials"))
)

pytestmark = pytest.mark.skipif(
    not _HAS_LIVE_S3,
    reason="live S3 smoke read requires ASANA_CACHE_S3_BUCKET + AWS creds (skipped in CI)",
)


def test_reader_derives_prefix_from_registry() -> None:
    """The reader's prefix is the registry's TASK_CACHE.prefix (the SSOT) — no literal."""
    reader = DurableTaskCacheReader()
    assert reader.prefix == TASK_CACHE.prefix
    assert reader.key_for(_LIVE_GID) == f"{TASK_CACHE.prefix}/tasks/{_LIVE_GID}/task.json"
    assert task_cache_key(_LIVE_GID) == reader.key_for(_LIVE_GID)


def test_live_reader_read_object_recovers_mrr_1500() -> None:
    """The reader's read_object reads the REAL live object -> MRR 1500 (Layer-4 grant proof)."""
    reader = DurableTaskCacheReader()
    client = reader.get_client()
    assert client is not None, "live boto3 S3 client must be resolvable with creds present"

    bucket = reader._resolve_bucket()
    assert bucket, "ASANA_CACHE_S3_BUCKET must resolve a bucket"

    task_data = reader.read_object(client, bucket, _LIVE_GID)
    assert task_data is not None, (
        f"live durable copy for gid {_LIVE_GID} must be present at "
        f"{reader.key_for(_LIVE_GID)} (bucket {bucket})"
    )
    mrr = get_custom_field_value(task_data, "MRR")
    assert mrr == _EXPECTED_MRR, (
        f"live MRR through the reader's read path must be {_EXPECTED_MRR} (got {mrr})"
    )
    print(
        f"\nFP-3 LIVE SMOKE: gid {_LIVE_GID} key={reader.key_for(_LIVE_GID)} "
        f"bucket={bucket} -> MRR={mrr}"
    )


async def test_live_reader_read_batch_recovers_mrr_1500() -> None:
    """The reader's async read_batch recovers the gid from REAL S3 -> MRR 1500."""
    reader = DurableTaskCacheReader()
    result = await reader.read_batch([_LIVE_GID])
    task_data = result.get(_LIVE_GID)
    assert task_data is not None, f"read_batch must recover gid {_LIVE_GID} from live S3"
    mrr = get_custom_field_value(task_data, "MRR")
    assert mrr == _EXPECTED_MRR, f"live batch MRR must be {_EXPECTED_MRR} (got {mrr})"
    print(f"\nFP-3 LIVE SMOKE (batch): reader.read_batch([{_LIVE_GID}]) -> MRR={mrr}")
