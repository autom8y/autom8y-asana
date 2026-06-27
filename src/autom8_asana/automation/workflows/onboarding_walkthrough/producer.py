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

import subprocess
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


class ProducerFreezeError(RuntimeError):
    """Raised when the producer subprocess fails to emit a valid frozen deck.

    Covers: non-zero exit, ADDR-NON-CANONICAL refusal, missing/empty output
    file, and the gated address being absent from the frozen output.
    """


def freeze_walkthrough_deck(
    *,
    producer_dir: Path,
    deck_template: str,
    gated_address: str,
    client_name: str,
    out_filename: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> bytes:
    """Shell ``node build/inline.mjs`` and return the frozen HTML bytes.

    Args:
        producer_dir: Directory containing the Node producer (``build/inline.mjs``)
            with a writable ``export/`` subdir. CONFIG -- never hardcoded.
        deck_template: Deck template folder name (e.g. ``"ghl-calendar-setup"``).
            The invoker prepends ``templates/``.
        gated_address: The canonical ``{uuid}@appointments.contenteapp.com``
            address resolved by the SDK (B1). Passed verbatim as ``--addr``;
            never reconstructed here (G-PROPAGATE P3).
        client_name: Clinic/business display name (``--client``). Cosmetic to
            the deck; not security-bearing.
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

    try:
        result = subprocess.run(  # noqa: S603 -- fixed argv, no shell; deck/out are workflow-controlled
            cmd,
            cwd=producer_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:  # node binary not on PATH (deploy precondition)
        raise ProducerFreezeError(
            f"producer entrypoint not runnable (node missing?): {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ProducerFreezeError(f"producer timed out after {timeout_s}s") from exc

    # Fail closed on any non-zero exit OR the explicit ADDR-NON-CANONICAL refusal
    # (the refusal IS a non-zero exit, but we check the sentinel for a precise
    # diagnostic and as defense against future exit-code drift).
    if result.returncode != 0 or ADDR_NON_CANONICAL_SENTINEL in (result.stderr or ""):
        stderr_snippet = (result.stderr or "").strip()[:500]
        logger.error(
            "walkthrough_producer_failed",
            returncode=result.returncode,
            stderr=stderr_snippet,
        )
        raise ProducerFreezeError(f"producer exit={result.returncode}: {stderr_snippet}")

    out_path = producer_dir / "export" / out_filename
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise ProducerFreezeError("producer exit 0 but no/empty output file")

    frozen = out_path.read_bytes()

    # Integrity re-validation (ADR-WALK-B3): the SDK-resolved gated address MUST
    # appear in the frozen output. A no-op/fallback renderer that exits 0 without
    # injecting the address is rejected here. This is a substring presence check
    # on bytes the producer already froze -- NOT a reimplementation of the freeze
    # mechanism (G-PROPAGATE P2 honored).
    if gated_address.encode("utf-8") not in frozen:
        raise ProducerFreezeError("frozen output missing the resolved gated address")

    return frozen
