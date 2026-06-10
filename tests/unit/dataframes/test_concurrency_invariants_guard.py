"""FROZEN-4 concurrency-invariant regression GUARD (CR-3 GATE-2 P0-b).

This is a TEST-ONLY guard. It asserts — and thereby makes un-droppable via config
or code drift — the four FROZEN-4 concurrency invariants that the receiver
bulk-fanout reliability fix (thermia cache-architecture ADR-001 + capacity-
specification PDR-002 §4.3, TD-001/TD-007) rests on. It changes NO production
value; it only ASSERTS the existing defaults and structural seams.

Each assertion carries a file:line docstring receipt (G-PROVE) pinning the
ground-truth source it guards:

  1. ``CacheSettings.cpu_thread_concurrency`` default == 4
     -> src/autom8_asana/settings.py:276-285
  2. ``CacheSettings.dataframe_max_concurrent_builds`` default == 4
     -> src/autom8_asana/settings.py:304-317
  3. ``run_cpu_bound`` is the SOLE CPU-offload seam — no CPU-bound merge
     (``pl.concat`` / ``*.concat``) is offloaded via a direct ``asyncio.to_thread``
     anywhere under src/ outside concurrency.py. (I/O ``to_thread`` sites are a
     SANCTIONED, allowlisted co-tenant — see the explicit allowlist below.)
     -> src/autom8_asana/dataframes/concurrency.py:18-23 (sole-seam discipline),
        :104 (Semaphore sizing), :166 (the single sanctioned to_thread)
  4. The BuildCoordinator semaphore is sized from ``max_concurrent_builds``.
     -> src/autom8_asana/cache/dataframe/build_coordinator.py:143 (field default 4),
        :153 (Semaphore(self.max_concurrent_builds))

If a future config/code change drops or weakens any invariant, exactly one of
these tests FAILS — that is the regression guard the FROZEN-4 contract requires.
"""

from __future__ import annotations

import ast
import inspect
import os
import textwrap
from pathlib import Path
from unittest.mock import patch

from autom8_asana.cache.dataframe import build_coordinator
from autom8_asana.dataframes import concurrency

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
_AUTOM8 = _SRC_ROOT / "autom8_asana"


# --------------------------------------------------------------------------- #
# Invariant 1 + 2: the FROZEN-4 settings defaults.
#
# Asserted on a freshly-constructed CacheSettings with a CLEARED environment so a
# CPU_THREAD_CONCURRENCY / ASANA_DF_MAX_CONCURRENT_BUILDS override in the runner
# cannot mask the in-code default we are guarding (idiom matches
# tests/unit/test_settings.py::TestAsanaSettings.test_default_values).
# --------------------------------------------------------------------------- #


def test_cpu_thread_concurrency_default_is_frozen_at_4() -> None:
    """cpu_thread_concurrency default MUST stay 4 (settings.py:276-285).

    The PDR-002 §4.3 CPU-offload gate is sized from this field; the default is
    FROZEN at 4 (== max_concurrent_builds) and is DANGEROUS to raise without a
    prior ECS CPU/mem task bump. This guard fails the instant the default drifts.
    """
    from autom8_asana.settings import CacheSettings

    with patch.dict(os.environ, {}, clear=True):
        cache = CacheSettings()

    assert cache.cpu_thread_concurrency == 4, (
        "FROZEN-4 violation: CacheSettings.cpu_thread_concurrency default is no "
        "longer 4 (guarded source: src/autom8_asana/settings.py:276-285). Raising "
        "this REQUIRES a prior verified ECS CPU/mem task bump (PDR-002 §4.3)."
    )


def test_dataframe_max_concurrent_builds_default_is_frozen_at_4() -> None:
    """dataframe_max_concurrent_builds default MUST stay 4 (settings.py:304-317).

    This is the PQ-1 build-concurrency headroom lever. It is config-overridable
    but the default is FROZEN at 4 this sprint; raising it is OQ-1-gated and needs
    a prior CPU/mem task bump (~4 x 2GB headroom vs current 2GB).
    """
    from autom8_asana.settings import CacheSettings

    with patch.dict(os.environ, {}, clear=True):
        cache = CacheSettings()

    assert cache.dataframe_max_concurrent_builds == 4, (
        "FROZEN-4 violation: CacheSettings.dataframe_max_concurrent_builds default "
        "is no longer 4 (guarded source: src/autom8_asana/settings.py:304-317). The "
        "lever is INERT and DANGEROUS to raise without a prior ECS task bump."
    )


# --------------------------------------------------------------------------- #
# Invariant 3: run_cpu_bound is the SOLE CPU-offload seam.
#
# `run_cpu_bound` is the only sanctioned path for offloading CPU-bound Polars work
# (pl.concat merge/checkpoint) per concurrency.py:18-23. A *bare* CPU merge
# offloaded by a direct `asyncio.to_thread(pl.concat, ...)` outside the gate
# re-creates the thread-pool / S3-persistence starvation PDR-002 was written to
# prevent.
#
# NOTE: `asyncio.to_thread` is NOT banned outright — that assertion would be
# FALSE. Direct `to_thread` is the SANCTIONED mechanism for blocking *I/O* offload
# (file reads/writes, boto3 / S3 persistence, observation-store appends). Those
# I/O sites are exactly the co-tenant the concurrency.py docstring names. We
# therefore (a) pin the single CPU-offload to_thread inside the gate, and (b)
# encode an explicit allowlist of the sanctioned non-CPU I/O to_thread sites,
# each with a file:line rationale — rather than weakening the assertion to a
# blanket "no to_thread".
# --------------------------------------------------------------------------- #

# Sanctioned non-CPU (blocking-I/O) asyncio.to_thread offload sites. Each is a
# file:line-grounded I/O offload, NOT a CPU-bound merge, and is therefore allowed
# to bypass the run_cpu_bound CPU gate. Verified at authorship via
# `grep -rn "asyncio.to_thread(" src/`. The KEY is a module path relative to
# src/; the VALUE is the rationale.
_SANCTIONED_IO_TO_THREAD: dict[str, str] = {
    # The single SANCTIONED CPU-offload to_thread — it lives INSIDE the gate and
    # IS run_cpu_bound's coupled offload (concurrency.py:166).
    "autom8_asana/dataframes/concurrency.py": (
        "the run_cpu_bound gate itself — the coupled to_thread inside the "
        "semaphore (concurrency.py:166)"
    ),
    # Blocking file I/O for attachment download/upload (read_bytes / open / write /
    # close) — I/O offload, not a CPU merge (attachments.py:328,473,482,485).
    "autom8_asana/clients/attachments.py": (
        "blocking attachment file I/O (read_bytes/open/write/close) — I/O offload"
    ),
    # S3 persistence I/O via boto3 (put/get/delete/list + client init). This is the
    # SAME default-pool co-tenant the CPU gate is sized to protect, not a CPU merge
    # (storage.py:457,525,592,653,1171).
    "autom8_asana/dataframes/storage.py": (
        "S3 persistence I/O via boto3 (put/get/delete/list/client) — I/O offload; "
        "the co-tenant the CPU gate protects"
    ),
    # Idempotency-store boto3 (DynamoDB) calls wrapped for the event loop — I/O
    # offload (idempotency.py:269,320,368,395).
    "autom8_asana/api/middleware/idempotency.py": (
        "idempotency-store boto3 (DynamoDB) calls — I/O offload"
    ),
    # Lifecycle observation-store append serialized via to_thread — I/O offload
    # (observation.py:171).
    "autom8_asana/lifecycle/observation.py": (
        "observation-store append serialization — I/O offload"
    ),
    # Automation event transport blocking boto3 publish — I/O offload
    # (transport.py:97).
    "autom8_asana/automation/events/transport.py": (
        "automation event transport boto3 publish — I/O offload"
    ),
    # DurableTaskCacheReader: the blessed bounded-concurrency durable S3 per-task
    # cache read (RAW boto3 get_object of {TASK_CACHE.prefix}/tasks/<gid>/task.json
    # — NOT S3CacheProvider, whose prefix + envelope deserialization were the #120
    # inert defect). This is where the FPC Phase-2 cure's cold-tier fill now lives:
    # the StorageNamespaceContract retire moved the raw-read LOGIC (and thus the
    # sole asyncio.to_thread offload site) OUT of null_number_recovery.py INTO this
    # reader module (subsumed, not duplicated). Blocking I/O offload, NOT a CPU
    # merge; semaphore-capped (ASANA_CURE_COLD_CONCURRENCY, default 24); 0 Asana
    # GETs (durable_task_cache.py:DurableTaskCacheReader.read_batch_with).
    "autom8_asana/cache/durable_task_cache.py": (
        "durable S3 per-task cache read (raw boto3 get_object) backfilling null "
        "numeric cf cells — I/O offload, semaphore-capped, 0 Asana GETs; the cure's "
        "cold-tier read logic subsumed here by the StorageNamespaceContract retire"
    ),
}


def _modules_with_real_to_thread_calls() -> set[str]:
    """Return src module paths (relative to src/) containing a real to_thread CALL.

    Parses each ``*.py`` under src/ and collects modules that contain an actual
    ``*.to_thread(...)`` *invocation* (an ``ast.Call`` whose func attr is
    ``to_thread``). Docstring/comment mentions of ``to_thread`` are NOT calls and
    are correctly ignored by the AST walk.
    """
    modules: set[str] = set()
    for py in _AUTOM8.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "to_thread"
            ):
                modules.add(str(py.relative_to(_SRC_ROOT)))
                break
    return modules


def test_no_unsanctioned_to_thread_offload_site() -> None:
    """run_cpu_bound is the sole CPU-offload seam (concurrency.py:18-23).

    Every direct ``asyncio.to_thread`` CALL site under src/ must be on the
    sanctioned I/O allowlist. A NEW direct to_thread call in an un-allowlisted
    module is a potential bare CPU offload that bypasses the load-bearing gate —
    the exact PDR-002 §4.3 regression this guards. New sanctioned I/O sites must be
    added to _SANCTIONED_IO_TO_THREAD with a file:line rationale (which forces a
    human to classify the new offload as I/O vs CPU).
    """
    found = _modules_with_real_to_thread_calls()
    unsanctioned = sorted(found - set(_SANCTIONED_IO_TO_THREAD))
    assert unsanctioned == [], (
        "Unsanctioned asyncio.to_thread offload site(s) detected: "
        f"{unsanctioned}. CPU-bound work MUST be offloaded via the shared "
        "run_cpu_bound gate (concurrency.py:18-23). If this is blocking I/O, add it "
        "to _SANCTIONED_IO_TO_THREAD with a file:line rationale after confirming it "
        "is NOT a CPU-bound merge."
    )


def test_run_cpu_bound_is_the_single_gated_cpu_offload() -> None:
    """The ONLY to_thread inside concurrency.py is run_cpu_bound's coupled offload.

    Guards concurrency.py:166 (``return await asyncio.to_thread(func, ...)``) AND
    the coupling at :160-166 (``async with semaphore`` wrapping the to_thread). The
    sole CPU-offload seam couples cap-acquisition and offload as one indivisible
    operation, so a call site cannot offload CPU work without passing the gate.
    """
    src = inspect.getsource(concurrency.run_cpu_bound)
    tree = ast.parse(textwrap.dedent(src))

    to_thread_calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "to_thread"
    ]
    assert len(to_thread_calls) == 1, (
        "run_cpu_bound must contain exactly one asyncio.to_thread offload "
        f"(concurrency.py:166); found {len(to_thread_calls)}."
    )

    has_async_with = any(isinstance(n, ast.AsyncWith) for n in ast.walk(tree))
    assert has_async_with, (
        "run_cpu_bound must couple the offload under `async with semaphore` so the "
        "cap is load-bearing by construction (concurrency.py:160-166)."
    )

    # The gate's own to_thread is the single concurrency.py site; the module-level
    # scan must classify concurrency.py as a sanctioned to_thread module.
    assert "autom8_asana/dataframes/concurrency.py" in _modules_with_real_to_thread_calls()


# --------------------------------------------------------------------------- #
# Invariant 4: the BuildCoordinator semaphore is sized from max_concurrent_builds.
# --------------------------------------------------------------------------- #


def test_build_coordinator_default_max_concurrent_builds_is_frozen_at_4() -> None:
    """BuildCoordinator.max_concurrent_builds default MUST stay 4 (build_coordinator.py:143).

    The dataclass default is FROZEN at 4 this sprint; it is config-overridable via
    cache.dataframe_max_concurrent_builds but the in-code default is the floor this
    guard pins.
    """
    fields = {
        f.name: f for f in __import__("dataclasses").fields(build_coordinator.BuildCoordinator)
    }
    assert "max_concurrent_builds" in fields, (
        "BuildCoordinator no longer declares max_concurrent_builds "
        "(guarded source: src/autom8_asana/cache/dataframe/build_coordinator.py:143)."
    )
    assert fields["max_concurrent_builds"].default == 4, (
        "FROZEN-4 violation: BuildCoordinator.max_concurrent_builds default is no "
        "longer 4 (src/autom8_asana/cache/dataframe/build_coordinator.py:143)."
    )


def test_build_coordinator_semaphore_is_sized_from_max_concurrent_builds() -> None:
    """BuildCoordinator sizes its semaphore from max_concurrent_builds (build_coordinator.py:153).

    Structural guard (AST): __post_init__ must construct
    ``asyncio.Semaphore(self.max_concurrent_builds)`` — NOT a literal. If a future
    change hardcodes a literal or sizes from a different attribute, the semaphore
    decouples from the FROZEN-4 lever and this fails.
    """
    src = inspect.getsource(build_coordinator.BuildCoordinator.__post_init__)
    tree = ast.parse(textwrap.dedent(src))

    sized_from_field = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Semaphore"
            and node.args
            and isinstance(node.args[0], ast.Attribute)
            and node.args[0].attr == "max_concurrent_builds"
            and isinstance(node.args[0].value, ast.Name)
            and node.args[0].value.id == "self"
        ):
            sized_from_field = True
            break

    assert sized_from_field, (
        "BuildCoordinator.__post_init__ must size its build semaphore from "
        "self.max_concurrent_builds (asyncio.Semaphore(self.max_concurrent_builds); "
        "guarded source: src/autom8_asana/cache/dataframe/build_coordinator.py:153). "
        "A literal or a different attribute decouples the FROZEN-4 lever."
    )


def test_build_coordinator_instance_semaphore_value_matches_max_concurrent_builds() -> None:
    """Behavioral: a constructed BuildCoordinator's semaphore _value == its cap.

    Complements the AST guard with a runtime check: the live semaphore admits
    exactly max_concurrent_builds slots, proving the sizing wiring is in effect at
    construction (build_coordinator.py:153).
    """
    coordinator = build_coordinator.BuildCoordinator()
    assert coordinator.max_concurrent_builds == 4
    assert coordinator._build_semaphore is not None
    assert coordinator._build_semaphore._value == coordinator.max_concurrent_builds, (
        "BuildCoordinator build semaphore is not sized from max_concurrent_builds "
        "(src/autom8_asana/cache/dataframe/build_coordinator.py:153)."
    )
