"""Harness-internal frame codec (S7 · WAVE-2 dark build).

The frozen ``substrate.serve.Provable`` carries an opaque ``frame: bytes``. For the
replay runner to check a *served-value match*, the harness needs to interpret that
frame. This module is the harness's OWN deterministic codec — clearly NOT a frozen
seam type and NOT v2's real frame encoding (which is parquet/arrow, S5-owned).

At S8 a thin adapter decodes the REAL v2 frame into ``FrameContent`` instead; in
wave-2 the reference substrate encodes it directly. Either way the runner reads the
served value + plane through one function, ``decode_frame``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tests.harness.substrate_gate.cases import SectionCell

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class FrameContent:
    """The harness-decoded content of a ``Provable.frame`` (harness-internal)."""

    served_value: float
    plane: str
    composition: Mapping[str, SectionCell]


def encode_frame(content: FrameContent) -> bytes:
    """Encode ``FrameContent`` to canonical UTF-8 JSON bytes (sorted keys)."""
    payload: dict[str, Any] = {
        "served_value": content.served_value,
        "plane": content.plane,
        "composition": {
            name: {"rows": cell.rows, "value": cell.value}
            for name, cell in sorted(content.composition.items())
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def decode_frame(frame: bytes) -> FrameContent:
    """Decode canonical frame bytes back to ``FrameContent``."""
    raw: Any = json.loads(frame.decode("utf-8"))
    composition: dict[str, SectionCell] = {
        str(name): SectionCell(rows=int(cell["rows"]), value=float(cell["value"]))
        for name, cell in raw["composition"].items()
    }
    return FrameContent(
        served_value=float(raw["served_value"]),
        plane=str(raw["plane"]),
        composition=composition,
    )
