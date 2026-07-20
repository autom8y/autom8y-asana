"""WS-2-EP pin-and-canary (A5) + semantic-lite gate (A7 noted).

The hand-authored tool schemas mirror native Pydantic models the sidecar must NOT
import (constraint 5). This canary reads the native source as TEXT (never imports
it) and trips if it drifts — signalling the hand-authored mirror needs re-review.

A7 note: the full semantic-score static gate is a production upgrade; sprint-2
ships the content-hash pin + a mirrored-field-token presence check (semantic-lite).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from asana_mcp.schemas import NATIVE_SOURCE

WORKTREE_ROOT = Path(__file__).resolve().parents[2]


def _native_models_path() -> Path:
    return WORKTREE_ROOT / NATIVE_SOURCE["rows_and_aggregate"]


def test_native_models_hash_pinned():
    models = _native_models_path()
    if not models.exists():
        pytest.skip(f"native models not present at {models} (out-of-worktree run)")
    actual = hashlib.sha256(models.read_bytes()).hexdigest()
    assert actual == NATIVE_SOURCE["rows_and_aggregate_sha256"], (
        "SCHEMA DRIFT: autom8_asana/query/models.py changed since the hand-authored "
        "asana_mcp/schemas.py mirror was pinned. Re-review RowsArgs/AggregateArgs "
        "against the native RowsRequest/AggregateRequest and re-pin the sha256."
    )


def test_mirrored_field_tokens_present_in_native_source():
    models = _native_models_path()
    if not models.exists():
        pytest.skip("native models not present (out-of-worktree run)")
    text = models.read_text()
    mirrored = NATIVE_SOURCE["mirrored_rows_fields"] + NATIVE_SOURCE["mirrored_aggregate_fields"]
    missing = [f for f in mirrored if f"{f}:" not in text]
    assert not missing, f"mirrored fields absent from native source (semantic drift): {missing}"
