"""Node >=22 producer subprocess invoker -- the SOLE walkthrough deck freezer.

Per ADR §3 (A2) / TDD §API Contracts / G-PROPAGATE P2: the deck is
render-then-frozen ONLY by the Node producer (`node build/inline.mjs`). This
module shells that producer and re-validates its output; it does NOT and MUST
NOT reimplement ``injectFrozenAddress`` / ``CANONICAL_ADDR_RE`` / MC-1 in
Python.

The output re-validation (ADR-WALK-B3) is an *integrity check on bytes the
producer already froze* -- it asserts the resolved gated address is present as a
literal substring. That is a presence check, NOT a re-derivation of the
canonical address form, so G-PROPAGATE P2 is honored.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import stat
import tempfile
import uuid
from pathlib import Path

from autom8y_log import get_logger

logger = get_logger(__name__)

# Sentinel the producer prints (to stderr, non-zero exit) when --addr is not a
# canonical {uuidv4}@appointments.contenteapp.com routing address.
# Receipt: producer build/inline.mjs:114-115 (ADDR-NON-CANONICAL refusal).
ADDR_NON_CANONICAL_SENTINEL = "ADDR-NON-CANONICAL"

# Producer entrypoint relative to the producer directory.
_PRODUCER_ENTRYPOINT = "build/inline.mjs"

# Default subprocess wall-clock budget (seconds). Cold-start/latency at
# Lambda/ECS scale is a separate BUILD PRECONDITION (NFR-5 / CON-2), not
# asserted here.
DEFAULT_TIMEOUT_S = 60.0

# Read-only-filesystem fallback (fault-9): stable name of the relocated producer
# tree under the runtime's writable tmp root, and the completion marker that
# distinguishes a COMPLETE copy from a partial one (warm invokes reuse the copy
# iff the marker is present).
_RELOCATED_TREE_NAME = "deck-producer"
_COPY_COMPLETE_MARKER = ".producer-copy-complete"


def _relocation_destination() -> Path:
    """Stable per-runtime destination for the relocated producer tree."""
    return Path(tempfile.gettempdir()) / _RELOCATED_TREE_NAME


def _export_dir_writable(producer_dir: Path) -> bool:
    """Probe whether the producer's ``export/`` dir can be created and written.

    Mirrors exactly what the producer does at emit() (``build/inline.mjs:197``
    ``mkdirSync(EXPORT_DIR, {recursive: true})`` then a write): attempt the
    mkdir plus a touch. On a read-only filesystem (Lambda: everything except
    ``/tmp``) the mkdir/touch raises -- the probe returns False BEFORE a
    subprocess is burned on a doomed run. On a writable tree (ECS) the probe
    passes and spawn behavior is unchanged (pre-creating ``export/`` is benign:
    the producer's own mkdir is recursive/exist-ok).
    """
    export_dir = producer_dir / "export"
    probe = export_dir / f".writability-probe-{uuid.uuid4().hex}"
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        probe.touch()
    except OSError:
        return False
    # Best-effort probe cleanup; writability is already proven.
    with contextlib.suppress(OSError):
        probe.unlink()
    return True


def _relocate_producer_tree(producer_dir: Path) -> Path:
    """Copy the producer tree to a stable writable location (COPY-ONCE).

    Lambda's filesystem is read-only except ``/tmp`` (production receipt
    2026-07-02T11:21:40Z: ``ENOENT: no such file or directory, mkdir
    '/app/vendor/deck-producer/export'``). Everything in the producer tree is
    relative to its own root (``build/inline.mjs`` derives ``EXPORT_DIR`` from
    ``__dirname``), so the copy preserves behavior byte-for-byte.

    Copy-once discipline: the tree (~264 files incl. node_modules; ~1-2s, paid
    ONCE per cold container) is copied on the first non-writable invocation;
    warm invokes reuse it via the completion marker. Partial-copy guard: copy
    to a unique staging name, stamp the marker INSIDE the staging tree, then
    atomically rename into place -- the stable path either does not exist or
    holds a complete, marker-stamped copy.
    """
    dest = _relocation_destination()
    marker = dest / _COPY_COMPLETE_MARKER
    if marker.exists():
        return dest  # warm invoke: reuse the completed copy

    staging = dest.with_name(f".{dest.name}-staging-{uuid.uuid4().hex}")
    shutil.copytree(producer_dir, staging, symlinks=True, dirs_exist_ok=False)
    # copytree mirrors the SOURCE root's mode onto the copy; a mode-read-only
    # source root would make the copy unwritable too. The copy MUST be writable
    # (that is its whole purpose): restore owner rwx on the copy root so the
    # marker, the export/ dir, and the frozen output can be created.
    staging.chmod(stat.S_IMODE(staging.stat().st_mode) | 0o700)
    (staging / _COPY_COMPLETE_MARKER).touch()
    try:
        staging.rename(dest)
    except OSError:
        if marker.exists():
            # Benign race: a concurrent invocation completed the rename first;
            # discard our redundant staging copy and use theirs.
            shutil.rmtree(staging, ignore_errors=True)
        else:
            raise
    return dest


class ProducerFreezeError(RuntimeError):
    """Raised when the producer subprocess fails to emit a valid frozen deck.

    Covers: non-zero exit, ADDR-NON-CANONICAL refusal, missing/empty output
    file, and the gated address being absent from the frozen output.
    """


async def freeze_walkthrough_deck(
    *,
    producer_dir: Path,
    deck_template: str,
    gated_address: str,
    client_name: str,
    title: str | None = None,
    out_filename: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> bytes:
    """Shell ``node build/inline.mjs`` and return the frozen HTML bytes.

    Read-only-filesystem fallback (fault-9): the producer hardcodes its export
    dir INSIDE its own tree (``build/inline.mjs:45-48`` -- no env/arg override;
    ``--out`` is only the filename), which ENOENTs on Lambda where everything
    except ``/tmp`` is read-only. Before spawning, ``{producer_dir}/export`` is
    probed for writability; if not writable the whole tree is relocated
    (copy-once, ~1-2s on the first cold invocation only) to a stable writable
    location and the producer is spawned from the copy. Writable trees (ECS)
    take the original path unchanged.

    Args:
        producer_dir: Directory containing the Node producer (``build/inline.mjs``)
            with a writable ``export/`` subdir. CONFIG -- never hardcoded. If the
            ``export/`` subdir is NOT writable (Lambda read-only fs), the tree is
            transparently relocated to a writable copy and spawned from there.
        deck_template: Deck template folder name (e.g. ``"email-forwarding-setup"``).
            The invoker prepends ``templates/``.
        gated_address: The canonical ``{uuid}@appointments.contenteapp.com``
            address resolved by the SDK (B1). Passed verbatim as ``--addr``;
            never reconstructed here (G-PROPAGATE P3).
        client_name: Clinic/business display name (``--client``). Cosmetic to
            the deck; not security-bearing.
        title: Customer-facing document title (``--title``), manifest-owned
            (fault-13/S5: without it the producer defaults the frozen
            ``<title>`` from ``--deck``). ``None`` omits the flag and relies on
            the producer's customer-safe default.
        out_filename: Relative output filename. The producer writes to
            ``{producer_dir}/export/{out_filename}`` (never an absolute path).
        timeout_s: Subprocess wall-clock budget.

    Returns:
        The frozen HTML as bytes.

    Raises:
        ProducerFreezeError: On non-zero exit, ADDR-NON-CANONICAL, missing/empty
            output, or the gated address being absent from the frozen output.
    """
    producer_dir = Path(producer_dir)

    # Fault-9 writability gate: relocate ONLY when the export dir is not
    # writable (Lambda). Writable trees (ECS) proceed exactly as before.
    relocated = False
    if not _export_dir_writable(producer_dir):
        try:
            producer_dir = _relocate_producer_tree(producer_dir)
        except OSError as exc:
            raise ProducerFreezeError(f"producer tree relocation failed: {exc}") from exc
        relocated = True
        logger.info(
            "walkthrough_producer_relocated",
            destination=str(producer_dir),
        )

    cmd = [
        "node",
        _PRODUCER_ENTRYPOINT,
        "--deck",
        f"templates/{deck_template}",
        "--addr",
        gated_address,
        "--client",
        client_name,
        "--out",
        out_filename,  # relative filename -> producer writes export/<out_filename>
    ]
    if title is not None:
        # Customer-facing <title> (fault-13/S5): manifest-owned, never the
        # internal template path the producer would otherwise derive.
        cmd.extend(["--title", title])

    # Native async subprocess (asyncio.create_subprocess_exec): the Python side
    # only awaits I/O on the child, consuming NO thread-pool slot -- so the
    # concurrency-invariants guard (test_no_unsanctioned_to_thread_offload_site)
    # stays green by ELIMINATION rather than by allowlisting a to_thread merge.
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=producer_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:  # node binary not on PATH (deploy precondition)
        raise ProducerFreezeError(
            f"producer entrypoint not runnable (node missing?): {exc}"
        ) from exc

    try:
        _stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise ProducerFreezeError(f"producer timed out after {timeout_s}s") from exc

    returncode = proc.returncode
    stderr = (stderr_b or b"").decode("utf-8", "replace")

    # Fail closed on any non-zero exit OR the explicit ADDR-NON-CANONICAL refusal
    # (the refusal IS a non-zero exit, but we check the sentinel for a precise
    # diagnostic and as defense against future exit-code drift).
    if returncode != 0 or ADDR_NON_CANONICAL_SENTINEL in stderr:
        stderr_snippet = stderr.strip()[:500]
        logger.error(
            "walkthrough_producer_failed",
            returncode=returncode,
            stderr=stderr_snippet,
        )
        raise ProducerFreezeError(f"producer exit={returncode}: {stderr_snippet}")

    out_path = producer_dir / "export" / out_filename
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise ProducerFreezeError("producer exit 0 but no/empty output file")

    frozen = out_path.read_bytes()

    if relocated:
        # The workflow's FR-8 export cleanup targets the CONFIGURED producer
        # dir and cannot see the relocated copy -- discharge the temp-file
        # cleanup here (best-effort; Lambda /tmp is runtime-ephemeral anyway)
        # so warm containers do not accumulate exports in /tmp.
        with contextlib.suppress(OSError):
            out_path.unlink()

    # Integrity re-validation (ADR-WALK-B3): the SDK-resolved gated address MUST
    # appear in the frozen output. A no-op/fallback renderer that exits 0 without
    # injecting the address is rejected here. This is a substring presence check
    # on bytes the producer already froze -- NOT a reimplementation of the freeze
    # mechanism (G-PROPAGATE P2 honored).
    if gated_address.encode("utf-8") not in frozen:
        raise ProducerFreezeError("frozen output missing the resolved gated address")

    return frozen
