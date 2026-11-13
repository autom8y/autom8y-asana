"""D6 delivery verification: header shape, body cap, byte compare, key cache, budget.

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.10, section 4 steps 2 to
6 (W F-2, A C-3, A C-8, A N-1, TM-5, TM-6), fixtures R-A1, SZ-1, ENC-1, KS-1, SM-1 and
RL-1 (section 9).

Everything here runs BEFORE any JSON parse, on the raw bytes Asana sent:

* ``Content-Encoding`` must be absent or ``identity`` (step 2). Anything else is 415.
* The body is capped at 256 KiB: a ``Content-Length`` over the cap is refused before any
  read, and the streamed read stops at the first byte past it (step 3, 413).
* ``X-Hook-Signature`` must appear exactly once and match ``^[0-9a-f]{64}$`` on the raw
  header bytes (step 4). Missing, empty, duplicated, non-ASCII or wrong-shape headers are
  401 and never trigger a key read.
* The compare is ``hmac.compare_digest`` on two ``bytes`` values, so no input can raise
  ``TypeError`` (W F-2: a ``str`` compare on non-ASCII input gave 500, not 401).
* Keys are cached for 5 minutes. A handle's key is read at most once per 60 seconds,
  single-flight: the first read on a cold cache and the one re-read after a mismatch
  share that window, so 1,000 mismatches cost at most one read (KS-1). The re-read runs
  only while the handle's failure budget (30 per minute) remains (TM-5).
* A key read that fails is :attr:`VerifyOutcome.KEY_UNAVAILABLE`, which the route answers
  with 500: never 401, and never a fallback key (A C-8, SM-1).

This module holds no AWS client. The key reader is an injected ``async`` callable; the
receiver wraps the store's blocking read in a thread.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterable

MAX_BODY_BYTES: Final[int] = 256 * 1024
KEY_CACHE_TTL_S: Final[int] = 300
KEY_READ_INTERVAL_S: Final[int] = 60
FAILURE_BUDGET_PER_WINDOW: Final[int] = 30
FAILURE_BUDGET_WINDOW_S: Final[int] = 60

SIGNATURE_HEADER: Final[bytes] = b"x-hook-signature"
CONTENT_ENCODING_HEADER: Final[bytes] = b"content-encoding"
CONTENT_LENGTH_HEADER: Final[bytes] = b"content-length"
_SIGNATURE_SHAPE: Final[re.Pattern[bytes]] = re.compile(rb"[0-9a-f]{64}")
_IDENTITY: Final[bytes] = b"identity"


class HeaderShape(StrEnum):
    OK = "ok"
    MISSING = "missing"
    DUPLICATED = "duplicated"
    MALFORMED = "malformed"


class VerifyOutcome(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    KEY_UNAVAILABLE = "key_unavailable"


class BodyTooLarge(Exception):
    """The body passed :data:`MAX_BODY_BYTES` (step 3, 413)."""


def header_values(raw_headers: Iterable[tuple[bytes, bytes]], name: bytes) -> list[bytes]:
    """Every raw value of header ``name`` (ASGI lowercases header names)."""
    return [value for key, value in raw_headers if key.lower() == name]


def encoding_permitted(raw_headers: Iterable[tuple[bytes, bytes]]) -> bool:
    """Step 2: ``Content-Encoding`` is absent, or every value is ``identity``."""
    for value in header_values(raw_headers, CONTENT_ENCODING_HEADER):
        tokens = [t.strip().lower() for t in value.split(b",")]
        if any(t != _IDENTITY for t in tokens):
            return False
    return True


def declared_length_too_large(raw_headers: Iterable[tuple[bytes, bytes]]) -> bool:
    """Step 3, before any read: a ``Content-Length`` that is over the cap or unreadable.

    An absent header is not refused here: the streamed read enforces the cap.
    """
    for value in header_values(raw_headers, CONTENT_LENGTH_HEADER):
        text = value.strip()
        if not text.isdigit() or int(text) > MAX_BODY_BYTES:
            return True
    return False


async def read_capped(chunks: AsyncIterator[bytes], cap: int = MAX_BODY_BYTES) -> bytes:
    """Read the request body, stopping at the first chunk that passes ``cap``.

    Raises :class:`BodyTooLarge` without reading further. The bytes returned are exactly
    the bytes received (ENC-1); nothing here decodes or rewrites them.
    """
    buffer = bytearray()
    async for chunk in chunks:
        buffer.extend(chunk)
        if len(buffer) > cap:
            raise BodyTooLarge
    return bytes(buffer)


def signature_header(raw_headers: Iterable[tuple[bytes, bytes]]) -> tuple[HeaderShape, bytes]:
    """Step 4: exactly one ``X-Hook-Signature`` of 64 lowercase hex, on the raw bytes."""
    values = header_values(raw_headers, SIGNATURE_HEADER)
    if not values:
        return HeaderShape.MISSING, b""
    if len(values) > 1:
        return HeaderShape.DUPLICATED, b""
    value = values[0]
    if not _SIGNATURE_SHAPE.fullmatch(value):
        return HeaderShape.MALFORMED, b""
    return HeaderShape.OK, value


def expected_signature(key: str, body: bytes) -> bytes:
    """HMAC-SHA256 of the raw body under ``key``, as lowercase hex ASCII bytes."""
    return hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest().encode("ascii")


def signature_matches(key: str, body: bytes, header: bytes) -> bool:
    """Constant-time compare of two ``bytes`` values (step 5)."""
    return hmac.compare_digest(expected_signature(key, body), header)


class FailureBudget:
    """Per-handle failure count over a fixed window (TM-5). Spending only skips step 6."""

    def __init__(
        self,
        *,
        limit: int = FAILURE_BUDGET_PER_WINDOW,
        window_s: int = FAILURE_BUDGET_WINDOW_S,
    ) -> None:
        self._limit = limit
        self._window_s = window_s
        self._counts: dict[str, tuple[int, int]] = {}

    def _current(self, handle: str, now: int) -> int:
        start, count = self._counts.get(handle, (now, 0))
        if now - start >= self._window_s:
            return 0
        return count

    def remaining(self, handle: str, now: int) -> int:
        return max(0, self._limit - self._current(handle, now))

    def spend(self, handle: str, now: int) -> None:
        start, count = self._counts.get(handle, (now, 0))
        if now - start >= self._window_s:
            start, count = now, 0
        self._counts[handle] = (start, count + 1)


@dataclass
class _CachedKey:
    key: str | None
    loaded_at: int | None
    last_read_at: int | None


class KeyUnavailable(Exception):
    """No key could be produced for the handle: a failed read, or one inside the window."""


class SignatureVerifier:
    """Steps 5 and 6: compare against the cached key; at most one read per handle per 60 s.

    ``read_key`` is an ``async`` callable that returns the handle's stored value, or
    raises. Every exception it raises is a failed read: the outcome is
    :attr:`VerifyOutcome.KEY_UNAVAILABLE`, never a mismatch and never a fallback key.
    """

    def __init__(
        self,
        *,
        read_key: Callable[[str], Awaitable[str]],
        budget: FailureBudget | None = None,
        cache_ttl_s: int = KEY_CACHE_TTL_S,
        read_interval_s: int = KEY_READ_INTERVAL_S,
    ) -> None:
        self._read_key = read_key
        self.budget = budget or FailureBudget()
        self._ttl_s = cache_ttl_s
        self._interval_s = read_interval_s
        self._entries: dict[str, _CachedKey] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _entry(self, handle: str) -> _CachedKey:
        return self._entries.setdefault(handle, _CachedKey(None, None, None))

    def _fresh_key(self, handle: str, now: int) -> str | None:
        entry = self._entry(handle)
        if entry.key is None or entry.loaded_at is None:
            return None
        return entry.key if now - entry.loaded_at < self._ttl_s else None

    def _may_read(self, handle: str, now: int) -> bool:
        last = self._entry(handle).last_read_at
        return last is None or now - last >= self._interval_s

    async def _read(self, handle: str, now: int, *, after_mismatch: bool) -> str | None:
        """Single-flight read. ``None`` when the window forbids a read (no key read)."""
        lock = self._locks.setdefault(handle, asyncio.Lock())
        async with lock:
            entry = self._entry(handle)
            if not after_mismatch:
                cached = self._fresh_key(handle, now)
                if cached is not None:
                    return cached  # another waiter loaded it while this one queued
            if not self._may_read(handle, now):
                return None
            entry.last_read_at = now
            try:
                key = await self._read_key(handle)
            except Exception as exc:  # noqa: BLE001
                # BROAD-CATCH: fail-closed -- any read failure is KEY_UNAVAILABLE (500),
                # never a mismatch and never a fallback key (A C-8). A key already cached
                # stays cached: the value is write-once, so a failed re-read cannot make
                # it wrong.
                raise KeyUnavailable(type(exc).__name__) from None
            entry.key, entry.loaded_at = key, now
            return key

    async def verify(self, handle: str, body: bytes, header: bytes, now: int) -> VerifyOutcome:
        key = self._fresh_key(handle, now)
        if key is None:
            try:
                key = await self._read(handle, now, after_mismatch=False)
            except KeyUnavailable:
                return VerifyOutcome.KEY_UNAVAILABLE
            if key is None:
                # Cold cache, and the last read (which failed) is inside the window.
                return VerifyOutcome.KEY_UNAVAILABLE
        if signature_matches(key, body, header):
            return VerifyOutcome.MATCH
        # Step 6: one re-read, only while the budget remains and the window allows it.
        if self.budget.remaining(handle, now) > 0 and self._may_read(handle, now):
            try:
                reread = await self._read(handle, now, after_mismatch=True)
            except KeyUnavailable:
                return VerifyOutcome.KEY_UNAVAILABLE
            if reread is not None and signature_matches(reread, body, header):
                return VerifyOutcome.MATCH
        self.budget.spend(handle, now)
        return VerifyOutcome.MISMATCH
