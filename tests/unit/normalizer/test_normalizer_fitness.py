"""Fitness-function tests for the scheduling-stratum normalizer-seam invariants.

Grep-zero polarity (per Phase-2 spec): each invariant is SATISFIED when the
forbidden pattern is ABSENT from the target source.  These are the same checks N5
re-fires at /qa; the resolver source is genuinely free of the forbidden literals
(documentation describes intent without invoking the banned symbols), so a naive
``grep -c`` returns 0.

Brittleness register defeated:
  * TL-A1 / B1 / B2 / B5 -- resolver purity (no persistence / I/O / mutation /
    concurrency / identity-re-resolution).
  * B3 -- cascade is data, not a hard-coded branch chain.
  * B4 (FORK-1 re-sourced) -- enrollment (``custom_cal_status``) stays ORTHOGONAL
    to the cascade + wire path: it is READ at the extractor ONLY (the pure
    projection's re-sourced enrollment axis) and appears nowhere in the resolver,
    the normalizer facade, or the push/wire path (enrollment rides as the derived
    ``enrolled`` bit).
  * B6 -- no follow-up booking-type classification in the resolver.
  * TL-A6 -- no legacy write-back target (``custom_cal_url`` / ``sql_chiropractors``)
    in the normalizer or the push path.  (``custom_cal_status`` is a legitimate READ
    under FORK-1 and is governed by B4, not TL-A6.)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import autom8_asana

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_SRC = Path(autom8_asana.__file__).parent
_RESOLVER = _SRC / "normalizer" / "scheduling_stratum.py"
_EXTRACTOR = _SRC / "normalizer" / "scheduling_extractor.py"
_NORMALIZER_INIT = _SRC / "normalizer" / "__init__.py"
_PUSH = _SRC / "services" / "scheduling_stratum_push.py"

# Resolver-purity forbidden patterns (TL-A1 / B1 / B2 / B5). Each is a regex that
# MUST NOT match the resolver source.
_PURITY_FORBIDDEN: dict[str, str] = {
    "orm-sqlalchemy": r"sqlalchemy",
    "orm-async-session": r"AsyncSession",
    "orm-session": r"\bSession\b",
    "asana-client": r"AsanaClient",
    "http-httpx": r"\bhttpx\b",
    "http-requests": r"\brequests\b",
    "http-aiohttp": r"\baiohttp\b",
    "aws-boto3": r"\bboto3\b",
    "mutation-set": r"\.set\(",
    "mutation-update": r"\.update\(",
    "concurrency-thread": r"threading\.Thread",
    "concurrency-create-task": r"asyncio\.create_task",
    "concurrency-threadmanager": r"ThreadManager",
    "identity-resolve-guid": r"resolve_guid_or_raise",
    "identity-office-phone": r"office_phone",
    "identity-sql-chiropractors": r"sql_chiropractors",
}

# B3 -- the cascade must never be a hard-coded provider branch chain.
_B3_FORBIDDEN = r"if\b.*reviewwave_id"

# B4 (FORK-1 re-sourced) -- the enrollment-status field.  ABSENT from the cascade
# resolver / normalizer facade / push-wire path (orthogonal); PRESENT at the
# extractor ONLY (the re-sourced enrollment axis).
_B4_STATUS = r"custom_cal_status"

# B6 -- follow-up booking classification, banned in the resolver.
_B6_FORBIDDEN: dict[str, str] = {
    "booking-type": r"booking_type",
    "tentative": r"Tentative",
    "standard": r"\bStandard\b",
}

# TL-A6 -- legacy write-back targets, banned in the normalizer + push path.  Under
# FORK-1 ``custom_cal_status`` is a legitimate READ (governed by B4, not here); the
# genuine never-touched legacy write targets remain banned everywhere.
_TLA6_FORBIDDEN: dict[str, str] = {
    "legacy-cal-url": r"custom_cal_url",
    "monolith-sql": r"sql_chiropractors",
}


def _matches(path: Path, pattern: str) -> list[str]:
    """Return the matching lines for ``pattern`` in ``path`` (empty == satisfied)."""
    text = path.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if re.search(pattern, line)]


@pytest.mark.parametrize(("name", "pattern"), sorted(_PURITY_FORBIDDEN.items()))
def test_resolver_purity_tl_a1_b1_b2_b5(name: str, pattern: str) -> None:
    """The pure resolver imports/uses none of the forbidden purity tokens."""
    hits = _matches(_RESOLVER, pattern)
    assert not hits, f"TL-A1/{name}: resolver must not contain /{pattern}/; found {hits}"


def test_b3_no_hardcoded_cascade_branch_chain() -> None:
    """B3: the cascade is the CASCADE_PRIORITY data, never an if-on-provider chain."""
    hits = _matches(_RESOLVER, _B3_FORBIDDEN)
    assert not hits, f"B3: resolver must not branch on a provider name; found {hits}"


@pytest.mark.parametrize("target", [_RESOLVER, _NORMALIZER_INIT, _PUSH])
def test_b4_status_absent_from_cascade_and_wire(target: Path) -> None:
    """B4: enrollment stays ORTHOGONAL to the cascade resolver + normalizer + wire.

    FORK-1 re-sources enrollment from ``custom_cal_status`` at the EXTRACTOR only;
    the cascade resolver, the normalizer facade, and the push/wire path never
    reference it -- enrollment rides as the derived ``enrolled`` bit.
    """
    hits = _matches(target, _B4_STATUS)
    assert not hits, f"B4: {target.name} must not reference custom_cal_status; found {hits}"


def test_b4_status_read_only_at_extractor() -> None:
    """B4 (positive / two-sided): the extractor IS the sole enrollment-read site.

    A vacuous 'absent everywhere' check would also pass if the extraction were
    silently dropped.  Assert the extractor genuinely reads ``custom_cal_status``,
    so the re-sourced enrollment axis is wired, not merely absent elsewhere.
    """
    hits = _matches(_EXTRACTOR, _B4_STATUS)
    assert hits, "B4: the extractor MUST read custom_cal_status (the re-sourced enrollment axis)"


@pytest.mark.parametrize(("name", "pattern"), sorted(_B6_FORBIDDEN.items()))
def test_b6_no_booking_classification_in_resolver(name: str, pattern: str) -> None:
    """B6: no follow-up booking-type / Tentative / Standard classification."""
    hits = _matches(_RESOLVER, pattern)
    assert not hits, f"B6/{name}: resolver must not contain /{pattern}/; found {hits}"


@pytest.mark.parametrize("target", [_RESOLVER, _EXTRACTOR, _NORMALIZER_INIT, _PUSH])
@pytest.mark.parametrize(("name", "pattern"), sorted(_TLA6_FORBIDDEN.items()))
def test_tl_a6_no_legacy_writeback(target: Path, name: str, pattern: str) -> None:
    """TL-A6: no legacy write-back target in the normalizer or the push path."""
    hits = _matches(target, pattern)
    assert not hits, f"TL-A6/{name}: {target.name} must not contain /{pattern}/; found {hits}"


def test_fitness_checker_has_teeth(tmp_path: Path) -> None:
    """Two-sided proof: the absence-check actually trips on a planted brittleness.

    A vacuous checker that never matches would pass every invariant above for the
    wrong reason. Plant each forbidden pattern into a synthetic source and assert
    the checker DETECTS it -- so a green run above is a real green, not a no-op.
    """
    planted = tmp_path / "planted.py"
    # A synthetic 'bad' normalizer that violates every invariant at once.
    planted.write_text(
        "import boto3\n"
        "from sqlalchemy.orm import Session, AsyncSession\n"
        "from autom8_asana.client import AsanaClient\n"
        "import httpx, requests, aiohttp\n"
        "from x import ThreadManager, resolve_guid_or_raise\n"
        "def bad(self):\n"
        "    if reviewwave_id:\n"
        "        self.custom_cal_status = 1\n"
        "        self.field.set(office_phone)\n"
        "        self.custom_cal_url = office_phone\n"
        "        sql_chiropractors.update(booking_type='Tentative')\n"
        "        threading.Thread(); asyncio.create_task(x())\n"
        "        return 'Standard'\n",
        encoding="utf-8",
    )
    all_patterns = [
        *_PURITY_FORBIDDEN.values(),
        _B3_FORBIDDEN,
        _B4_STATUS,
        *_B6_FORBIDDEN.values(),
        *_TLA6_FORBIDDEN.values(),
    ]
    undetected = [p for p in all_patterns if not _matches(planted, p)]
    assert not undetected, f"checker is vacuous -- failed to detect planted: {undetected}"
