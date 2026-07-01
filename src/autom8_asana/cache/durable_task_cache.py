"""DurableTaskCacheReader — the blessed explicit read API for the TASK_CACHE namespace.

This formalizes the #121 cure's ad-hoc raw-boto3 read pattern as a named,
registerable owner in the storage namespace registry. It is NOT a tiered cache
tier: the ``asana-cache/tasks/`` namespace is WRITE-durable (written by the
durable-first warm path) with EXPLICIT read via this class. There is no S3 cold
tier in the cache provider stack — the phantom was retired (see
``StorageNamespaceContract.TASK_CACHE.lifecycle_note`` and the retirement of
``TieredConfig.s3_enabled``).

Why a RAW S3 GET and NOT ``S3CacheProvider`` (the #120 inert-cure correction)
-----------------------------------------------------------------------------
The durable per-task copies at ``{TASK_CACHE.prefix}/tasks/{gid}/task.json`` are
RAW Asana task dicts (top-level ``gid``/``custom_fields``/``name``), written by the
warmer's durable-first path — NOT ``S3CacheProvider``-serialized envelopes.
``S3CacheProvider._deserialize_entry`` reads ``data.get("data", {})`` and so
surfaces nothing from a raw task dict. And ``S3CacheProvider(prefix=...)`` would
read the OVERLOADED ``ASANA_CACHE_S3_PREFIX`` (prod: ``asana-cache/project-frames/``),
landing on an EMPTY namespace. This reader therefore reads the objects exactly as
the proven live probe does: a raw ``boto3`` ``get_object`` (with a ``.gz``
fallback), ``json.loads`` the body, then ``raw.get("data", raw)`` to unwrap an
optional Asana ``{"data": {...}}`` envelope.

Prefix derivation (SSOT)
------------------------
The read prefix DERIVES from ``StorageNamespaceContract.TASK_CACHE.prefix`` — it is
NOT pinned as a loose literal and NOT read from ``get_settings().s3.prefix``. This
is the contract's whole point: the prefix lives in ONE place (the registry), so a
wrong-prefix read is structurally unaddressable (``tests/arch/test_namespace_contract.py``
t3 forbids the literal anywhere else in ``src/``). Only the BUCKET comes from
settings (``ASANA_CACHE_S3_BUCKET`` is single-purpose, not overloaded).

Concurrency
-----------
S3 has no batch GET, so reading N gids is N blocking ``client.get_object`` calls.
A single worker reading N keys serially is linear and unbounded in N (timeout-cliff
risk on the live unit warm, N~3021). The batch read fans the per-gid GETs out
across worker threads, capping the in-flight count with an ``asyncio.Semaphore``
(env ``ASANA_CURE_COLD_CONCURRENCY``, clamped to ``[1, 64]``, default 24). Each GET
runs in its own ``asyncio.to_thread`` so no read blocks the event loop. This is the
SOLE ``asyncio.to_thread`` site for the durable cache read (the concurrency guard's
``_SANCTIONED_IO_TO_THREAD`` allowlist names THIS module as the offload site).
"""

from __future__ import annotations

import gzip
import json
import os
import threading
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.storage_namespace import TASK_CACHE

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "COLD_CONCURRENCY_DEFAULT",
    "COLD_CONCURRENCY_ENV",
    "COLD_CONCURRENCY_MAX",
    "COLD_CONCURRENCY_MIN",
    "DurableTaskCacheReader",
    "get_durable_task_cache_reader",
    "task_cache_key",
    "unwrap_task_data",
]

logger = get_logger(__name__)

# Cold-read fan-out concurrency cap, env-overridable and clamped to a sane range.
# A misconfigured value can neither serialize the read (0/negative -> clamped to
# MIN) nor exhaust the connection / thread pool (absurd -> clamped to MAX).
COLD_CONCURRENCY_DEFAULT = 24
COLD_CONCURRENCY_MIN = 1
COLD_CONCURRENCY_MAX = 64
COLD_CONCURRENCY_ENV = "ASANA_CURE_COLD_CONCURRENCY"


def _cold_concurrency() -> int:
    """Resolve the cold-read fan-out cap from the env, clamped to ``[MIN, MAX]``.

    A missing/blank/garbage value falls back to ``COLD_CONCURRENCY_DEFAULT``.
    """
    raw = os.environ.get(COLD_CONCURRENCY_ENV)
    if raw is None or not raw.strip():
        value = COLD_CONCURRENCY_DEFAULT
    else:
        try:
            value = int(raw.strip())
        except ValueError:
            value = COLD_CONCURRENCY_DEFAULT
    return max(COLD_CONCURRENCY_MIN, min(COLD_CONCURRENCY_MAX, value))


def task_cache_key(gid: str) -> str:
    """The canonical durable per-task cache key for ``gid``.

    ``{TASK_CACHE.prefix}/tasks/{gid}/task.json`` — the namespace the warmer's
    durable-first write path uses. The prefix DERIVES from the registry
    (``TASK_CACHE.prefix``), decoupled from the env-overloaded
    ``get_settings().s3.prefix`` (see module docstring).
    """
    return f"{TASK_CACHE.prefix}/tasks/{gid}/task.json"


def unwrap_task_data(data: Any) -> dict[str, Any] | None:
    """Return the task dict from a raw S3 payload, unwrapping a ``{"data": ...}`` envelope.

    The durable per-task copies are RAW Asana task dicts (top-level
    ``gid``/``custom_fields``/``name``). Some warmer paths persist the API response
    verbatim, which carries a ``{"data": {...}}`` Asana envelope. Mirrors the proven
    probe's ``raw.get("data", raw)`` unwrap so the downstream ``custom_fields``
    lookup sees a top-level task dict either way.
    """
    if not isinstance(data, dict):
        return None
    inner = data.get("data")
    if isinstance(inner, dict):
        return inner
    return data


class DurableTaskCacheReader:
    """Explicit read API for the TASK_CACHE namespace (raw boto3, registry-pinned prefix).

    NOT a tiered cache tier. The ``asana-cache/tasks/`` namespace is WRITE-durable
    with EXPLICIT read via this class. There is no S3 cold tier in the cache
    provider stack — the phantom was retired.

    The reader lazily builds ONE module-cached boto3 client (boto3 low-level
    clients are thread-safe for method calls, so ONE shared client serves the
    fan-out; the lock guards only the lazy first-build, never the GET path). A
    build failure (missing boto3 / creds / bucket) memoizes ``None`` so we do not
    retry construction on every call; the reader then stays a clean no-op.
    """

    def __init__(self) -> None:
        # The read prefix derives from the registry, NOT from settings.
        self._prefix = TASK_CACHE.prefix
        self._client: Any = None
        self._client_lock = threading.Lock()
        # Distinguishes "not yet built" from "built and failed -> None" (a
        # missing-creds posture is sticky within a process).
        self._client_build_attempted = False

    @property
    def prefix(self) -> str:
        """The registry-derived task-cache prefix (``TASK_CACHE.prefix``)."""
        return self._prefix

    def key_for(self, gid: str) -> str:
        """The canonical durable key for ``gid`` (delegates to ``task_cache_key``)."""
        return task_cache_key(gid)

    def reset_client(self) -> None:
        """Drop the module-cached boto3 client so the next read rebuilds it.

        Used by the live smoke (to build a fresh REAL client) and by unit tests
        (to install a fake between cases). A no-op on the GET path.
        """
        with self._client_lock:
            self._client = None
            self._client_build_attempted = False

    def get_client(self) -> Any | None:
        """Return the module-cached boto3 S3 client, building it lazily once.

        Bucket/region come from ``get_settings().s3`` (the BUCKET env is NOT
        overloaded; only the PREFIX is — which is why the prefix derives from the
        registry instead). Never raises: a build failure memoizes ``None``.
        """
        if self._client_build_attempted:
            return self._client
        with self._client_lock:
            # Double-checked: a sibling thread may have built it while we waited.
            if self._client_build_attempted:
                return self._client
            try:
                import boto3

                from autom8_asana.settings import get_settings

                s3 = get_settings().s3
                if not s3.bucket:
                    self._client = None
                else:
                    client_kwargs: dict[str, Any] = {"region_name": s3.region}
                    if s3.endpoint_url:
                        client_kwargs["endpoint_url"] = s3.endpoint_url
                    self._client = boto3.client("s3", **client_kwargs)
            except Exception:  # BROAD-CATCH: client build is best-effort  # noqa: BLE001
                self._client = None
            self._client_build_attempted = True
            return self._client

    def _resolve_bucket(self) -> str:
        """Resolve the S3 bucket from settings; ``""`` on any failure (clean no-op)."""
        try:
            from autom8_asana.settings import get_settings

            return get_settings().s3.bucket or ""
        except Exception:  # BROAD-CATCH: settings read is best-effort  # noqa: BLE001
            return ""

    def read_object(self, client: Any, bucket: str, gid: str) -> dict[str, Any] | None:
        """Raw S3 GET of one per-task copy. Mirrors the proven probe's ``read_cache_s3``.

        GETs ``{prefix}/tasks/{gid}/task.json`` (with a ``.gz`` fallback), gunzips a
        compressed body, ``json.loads`` it, and unwraps an optional ``{"data": {...}}``
        Asana envelope. Returns the task dict, or ``None`` on a 404 / NoSuchKey
        (honest cache-miss) or an undecodable body. Any OTHER per-gid error
        propagates to the caller (which logs ONE warning and maps the gid to None).
        """
        base = self.key_for(gid)
        last_exc: Exception | None = None
        for key in (base, base + ".gz"):
            try:
                obj = client.get_object(Bucket=bucket, Key=key)
                body = obj["Body"].read()
                if key.endswith(".gz"):
                    body = gzip.decompress(body)
                raw = json.loads(body)
                return unwrap_task_data(raw)
            except Exception as e:  # classified just below
                name = type(e).__name__
                # NoSuchKey / 404 on the un-suffixed key just means "try the .gz"
                # and, if that also misses, honest cache-miss (None). A malformed
                # body (JSON / gzip error) on a key that DID exist is also an
                # honest-null for that gid — a corrupt durable copy must not crash.
                if name in ("NoSuchKey", "404") or "NoSuchKey" in str(e) or "Not Found" in str(e):
                    last_exc = e
                    continue
                if isinstance(e, ValueError | OSError):  # json.JSONDecodeError, gzip.BadGzipFile
                    return None
                # An unexpected error (creds, throttle, network) — surface it so the
                # caller logs exactly one warning for this gid and maps it to None.
                raise
        # Both keys missed (NoSuchKey on each): honest cache-miss.
        _ = last_exc
        return None

    async def read_batch(self, gids: list[str]) -> dict[str, dict[str, Any] | None]:
        """Bounded-concurrency RAW-S3 read of the durable per-task copies for ``gids``.

        Resolves the client + bucket from the reader's own lazy state, then delegates
        the fan-out to :meth:`read_batch_with`. Returns ``{gid: task_dict | None}``.
        """
        client = self.get_client()
        if client is None:
            return {}
        bucket = self._resolve_bucket()
        if not bucket:
            return {}
        return await self.read_batch_with(client, bucket, gids, self.read_object)

    async def read_batch_with(
        self,
        client: Any,
        bucket: str,
        gids: list[str],
        read_fn: Callable[[Any, str, str], dict[str, Any] | None],
    ) -> dict[str, dict[str, Any] | None]:
        """Bounded-concurrency fan-out of ``read_fn`` over ``gids`` against ``client``.

        This is the SOLE ``asyncio.to_thread`` offload site for the durable cache
        read (the concurrency guard's ``_SANCTIONED_IO_TO_THREAD`` allowlist names
        THIS module). ``read_fn(client, bucket, gid) -> dict | None`` is injected so
        a consumer (the #121 cure) can supply its own — possibly test-patched —
        per-gid reader while the bounded fan-out logic lives here, once.

        Fans the per-gid reads out across worker threads, capping the in-flight count
        with an ``asyncio.Semaphore`` (see ``_cold_concurrency``). Each read runs in
        its own ``asyncio.to_thread`` so no read blocks the event loop.

        Invariants preserved:
          * **not-N+1 at gid granularity.** EXACTLY one read per distinct gid —
            no per-row/per-cell amplification (the fan-out parallelizes, never
            multiplies).
          * **Zero Asana GETs.** S3 is durable CACHE, not Asana.
          * **never-fabricate.** A miss / undecodable body -> ``None``.
          * **additive / never-raises.** A per-gid error contributes ``None``; a
            total failure returns ``{}``. No exception escapes.
          * **idempotent re-warm.** A pure read; re-running yields the same map.

        Thread-safety: boto3 low-level clients are thread-safe for method calls and
        we share ONE client across the fan-out, so concurrent reads race-free.
        """
        import asyncio

        cap = _cold_concurrency()
        sem = asyncio.Semaphore(cap)

        async def _one(gid: str) -> tuple[str, dict[str, Any] | None]:
            # One read per gid, off the event loop, gated by the semaphore so at most
            # ``cap`` reads are in flight at once. A per-gid failure -> None (honest-null).
            async with sem:
                try:
                    task_data = await asyncio.to_thread(read_fn, client, bucket, gid)
                except Exception as e:  # BROAD-CATCH: per-gid read is additive  # noqa: BLE001
                    logger.warning(
                        "durable_task_cache_read_gid_failed",
                        extra={"gid": gid, "error": str(e), "error_type": type(e).__name__},
                    )
                    return gid, None
            return gid, task_data

        try:
            pairs = await asyncio.gather(*[_one(g) for g in gids])
        except Exception as e:  # BROAD-CATCH: total cold read is additive  # noqa: BLE001
            logger.warning(
                "durable_task_cache_read_failed",
                extra={"gid_count": len(gids), "error": str(e), "error_type": type(e).__name__},
            )
            return {}

        return dict(pairs)


# Module-cached singleton reader. ONE reader per process shares ONE boto3 client
# across every durable read (the cure's cold-tier fill is the primary consumer).
_READER: DurableTaskCacheReader | None = None
_READER_LOCK = threading.Lock()


def get_durable_task_cache_reader() -> DurableTaskCacheReader:
    """Return the process-wide ``DurableTaskCacheReader`` singleton (lazy-built)."""
    global _READER
    if _READER is not None:
        return _READER
    with _READER_LOCK:
        if _READER is None:
            _READER = DurableTaskCacheReader()
        return _READER
