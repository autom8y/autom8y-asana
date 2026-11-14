"""D6 delivery verification: R-A1 shapes, SZ-1, ENC-1, KS-1, SM-1, TM-5 (TDD r4.10 s4, s9).

Unit tests of ``trigger.signature``: no network, no AWS. Each refusal has a passing twin,
and the key reader counts its calls, so "at most one read" is a measured number. Every
hook value and body is generated at runtime.
"""

from __future__ import annotations

import secrets
from typing import Any

import pytest

from autom8_asana.trigger.signature import (
    MAX_BODY_BYTES,
    BodyTooLarge,
    FailureBudget,
    HeaderShape,
    SignatureVerifier,
    VerifyOutcome,
    declared_length_too_large,
    encoding_permitted,
    read_capped,
    signature_header,
    signature_matches,
)
from tests.unit.trigger.conftest import body_stream, runtime_hook_value, sign

SIG = b"x-hook-signature"


class Reader:
    """An async key reader that counts reads and can fail."""

    def __init__(self, value: str, *, fail: bool = False) -> None:
        self.value = value
        self.fail = fail
        self.reads = 0

    async def __call__(self, handle: str) -> str:
        self.reads += 1
        if self.fail:
            raise RuntimeError("simulated read failure")
        return self.value


def _handle() -> str:
    return secrets.token_hex(16)


# ---------------------------------------------------------------------------
# Step 4 (R-A1): the header shape, on raw bytes
# ---------------------------------------------------------------------------


def test_one_lowercase_hex_signature_header_passes() -> None:
    """R-A1 twin (D6 TDD fixture or review id)."""
    value = sign(runtime_hook_value(), b"{}").encode("ascii")
    assert signature_header([(SIG, value)]) == (HeaderShape.OK, value)


@pytest.mark.parametrize(
    ("headers", "shape"),
    [
        ([], HeaderShape.MISSING),
        ([(SIG, b"")], HeaderShape.MALFORMED),
        ([(SIG, b"a" * 64), (SIG, b"a" * 64)], HeaderShape.DUPLICATED),
        ([(SIG, b"A" * 64)], HeaderShape.MALFORMED),  # uppercase hex
        ([(SIG, b"a" * 63)], HeaderShape.MALFORMED),
        ([(SIG, b"a" * 65)], HeaderShape.MALFORMED),
        ([(SIG, "é".encode() * 32)], HeaderShape.MALFORMED),  # non-ASCII bytes
        ([(SIG, b"a" * 63 + b"\n")], HeaderShape.MALFORMED),
        ([(SIG, b" " + b"a" * 64)], HeaderShape.MALFORMED),
    ],
    ids=[
        "missing",
        "empty",
        "duplicated",
        "uppercase",
        "short",
        "long",
        "non-ascii",
        "newline",
        "space",
    ],
)
def test_malformed_signature_headers_are_refused(
    headers: list[tuple[bytes, bytes]], shape: HeaderShape
) -> None:
    """R-A1 (D6 TDD fixture or review id)."""
    assert signature_header(headers) == (shape, b"")


def test_compare_is_on_bytes_so_non_ascii_cannot_raise() -> None:
    """R-A1, W F-2: W F-2: a str compare_digest raised TypeError on non-ASCII; a bytes compare cannot."""
    value = runtime_hook_value()
    assert signature_matches(value, b"{}", "é".encode() * 32) is False
    assert signature_matches(value, b"{}", sign(value, b"{}").encode("ascii")) is True


def test_another_hooks_key_does_not_match() -> None:
    """R-A1: A's signature sent to B."""
    body = b'{"events":[]}'
    assert not signature_matches(
        runtime_hook_value(), body, sign(runtime_hook_value(), body).encode()
    )


# ---------------------------------------------------------------------------
# Steps 2 and 3 (ENC-1, SZ-1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [b"gzip", b"br", b"deflate", b"identity, gzip", b"x-gzip"])
def test_any_content_coding_but_identity_is_refused(value: bytes) -> None:
    """ENC-1 (D6 TDD fixture or review id)."""
    assert encoding_permitted([(b"content-encoding", value)]) is False


@pytest.mark.parametrize(
    "headers", [[], [(b"content-encoding", b"identity")], [(b"content-encoding", b" Identity ")]]
)
def test_absent_or_identity_content_coding_passes(headers: list[tuple[bytes, bytes]]) -> None:
    """ENC-1 twin (D6 TDD fixture or review id)."""
    assert encoding_permitted(headers) is True


def test_declared_length_over_the_cap_is_refused_before_any_read() -> None:
    """SZ-1 (D6 TDD fixture or review id)."""
    over = str(MAX_BODY_BYTES + 1).encode()
    assert declared_length_too_large([(b"content-length", over)]) is True
    assert declared_length_too_large([(b"content-length", b"not-a-number")]) is True
    assert declared_length_too_large([(b"content-length", str(MAX_BODY_BYTES).encode())]) is False
    assert declared_length_too_large([]) is False


async def test_streamed_body_stops_at_the_first_chunk_past_the_cap() -> None:
    """SZ-1 (D6 TDD fixture or review id)."""
    chunk = b"x" * (64 * 1024)
    pulled = {"n": 0}

    async def endless() -> Any:
        while True:
            pulled["n"] += 1
            yield chunk

    with pytest.raises(BodyTooLarge):
        await read_capped(endless())
    # 256 KiB is four chunks; the fifth passes the cap and the read stops there.
    assert pulled["n"] == 5


async def test_200_kib_body_passes_with_bytes_unchanged() -> None:
    """SZ-1 twin, ENC-1 (D6 TDD fixture or review id)."""
    body = secrets.token_bytes(200 * 1024)
    assert await read_capped(body_stream(body[:7], body[7:])) == body


# ---------------------------------------------------------------------------
# Steps 5 and 6 (KS-1, SM-1, TM-5)
# ---------------------------------------------------------------------------


async def test_matching_signatures_read_the_key_once_and_cache_it() -> None:
    """KS-1 twin (D6 TDD fixture or review id)."""
    value = runtime_hook_value()
    reader = Reader(value)
    verifier = SignatureVerifier(read_key=reader)
    handle, body = _handle(), b'{"events":[]}'
    for i in range(20):
        outcome = await verifier.verify(handle, body, sign(value, body).encode(), now=1000 + i)
        assert outcome is VerifyOutcome.MATCH
    assert reader.reads == 1


async def test_a_thousand_mismatches_cost_at_most_one_key_read() -> None:
    """KS-1 (D6 TDD fixture or review id)."""
    reader = Reader(runtime_hook_value())
    verifier = SignatureVerifier(read_key=reader)
    handle, body = _handle(), b'{"events":[]}'
    forged = sign(runtime_hook_value(), body).encode()
    outcomes = {await verifier.verify(handle, body, forged, now=5000) for _ in range(1000)}
    assert outcomes == {VerifyOutcome.MISMATCH}
    assert reader.reads <= 1
    assert verifier.budget.remaining(handle, 5000) == 0


async def test_without_the_read_window_every_mismatch_would_read() -> None:
    """KS-1 teeth: The bound comes from the 60 s window: with a zero window, reads track mismatches."""
    reader = Reader(runtime_hook_value())
    verifier = SignatureVerifier(read_key=reader, read_interval_s=0)
    handle, body = _handle(), b"{}"
    forged = sign(runtime_hook_value(), body).encode()
    for _ in range(10):
        await verifier.verify(handle, body, forged, now=5000)
    assert reader.reads > 1


async def test_reread_after_mismatch_waits_for_the_read_window() -> None:
    """TM-5 (D6 TDD fixture or review id)."""
    value = runtime_hook_value()
    reader = Reader(value)
    verifier = SignatureVerifier(read_key=reader)
    handle, body = _handle(), b"{}"
    forged = sign(runtime_hook_value(), body).encode()
    await verifier.verify(handle, body, forged, now=100)  # cold load: read 1
    await verifier.verify(handle, body, forged, now=130)  # inside the window: no read
    assert reader.reads == 1
    await verifier.verify(handle, body, forged, now=161)  # window passed, budget left
    assert reader.reads == 2


async def test_an_exhausted_failure_budget_skips_the_reread() -> None:
    """TM-5 (D6 TDD fixture or review id)."""
    reader = Reader(runtime_hook_value())
    budget = FailureBudget(limit=1, window_s=600)
    verifier = SignatureVerifier(read_key=reader, budget=budget)
    handle, body = _handle(), b"{}"
    forged = sign(runtime_hook_value(), body).encode()
    await verifier.verify(handle, body, forged, now=100)  # read 1, spends the budget
    await verifier.verify(handle, body, forged, now=170)  # window passed, budget spent
    assert reader.reads == 1
    assert (await verifier.verify(handle, body, forged, now=170)) is VerifyOutcome.MISMATCH


async def test_failed_key_read_is_unavailable_never_a_mismatch() -> None:
    """SM-1, A C-8: A C-8: a read error gives 500 (KEY_UNAVAILABLE), never 401, never a fallback key."""
    reader = Reader(runtime_hook_value(), fail=True)
    verifier = SignatureVerifier(read_key=reader)
    handle, body = _handle(), b"{}"
    outcome = await verifier.verify(handle, body, sign(reader.value, body).encode(), now=100)
    assert outcome is VerifyOutcome.KEY_UNAVAILABLE
    # Inside the window there is no key and no read: still unavailable, still no 401.
    again = await verifier.verify(handle, body, sign(reader.value, body).encode(), now=110)
    assert again is VerifyOutcome.KEY_UNAVAILABLE
    assert reader.reads == 1


async def test_failed_reread_on_a_mismatch_is_unavailable() -> None:
    """SM-1 (D6 TDD fixture or review id)."""
    value = runtime_hook_value()
    reader = Reader(value)
    verifier = SignatureVerifier(read_key=reader)
    handle, body = _handle(), b"{}"
    assert (await verifier.verify(handle, body, sign(value, body).encode(), now=100)) is (
        VerifyOutcome.MATCH
    )
    reader.fail = True
    forged = sign(runtime_hook_value(), body).encode()
    assert (await verifier.verify(handle, body, forged, now=200)) is VerifyOutcome.KEY_UNAVAILABLE
    # The cached key survives a failed re-read: the value is write-once.
    assert (await verifier.verify(handle, body, sign(value, body).encode(), now=201)) is (
        VerifyOutcome.MATCH
    )


async def test_single_flight_concurrent_cold_requests_share_one_read() -> None:
    import asyncio

    value = runtime_hook_value()
    gate = asyncio.Event()
    reads = {"n": 0}

    async def slow_reader(handle: str) -> str:
        reads["n"] += 1
        await gate.wait()
        return value

    verifier = SignatureVerifier(read_key=slow_reader)
    handle, body = _handle(), b"{}"
    header = sign(value, body).encode()
    tasks = [asyncio.create_task(verifier.verify(handle, body, header, now=100)) for _ in range(25)]
    await asyncio.sleep(0)
    gate.set()
    assert {await t for t in tasks} == {VerifyOutcome.MATCH}
    assert reads["n"] == 1


def test_budget_window_resets() -> None:
    budget = FailureBudget(limit=2, window_s=60)
    handle = _handle()
    budget.spend(handle, 0)
    budget.spend(handle, 1)
    assert budget.remaining(handle, 2) == 0
    assert budget.remaining(handle, 61) == 2
