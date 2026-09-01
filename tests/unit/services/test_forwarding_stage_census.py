"""Forwarding-Stage census — TOTAL-or-refuse, with two-sided tripwire teeth.

★ WHAT THIS MODULE IS ACTUALLY PROVING
---------------------------------------
The census is the SECOND OPERAND of the EBI F3 cross-source tripwire. Its only
job is to be a number the tripwire can trust. So the teeth are not "does the
function count" — they are:

  1. Given a corpus whose TRUE Verified count is KNOWN, does the census produce
     exactly that, across MULTIPLE pages? (AGREE)
  2. Given a keyspace that has lost clinics, does the difference DISAGREE with
     the right sign and magnitude? (DISAGREE — the tripwire's first job is to
     prove it can disagree.)
  3. Given a transport that SILENTLY TRUNCATES — the S-3 defect class, the one
     named in advance for this leg — does the census REFUSE rather than emit a
     first-page count that would manufacture a FALSE DISAGREE?

(3) is the load-bearing one. A census that under-reports does not fail loudly;
it makes the tripwire cry wolf, and a tripwire that cries wolf discredits itself
faster than one that stays silent.

★ THE RED ARMS ARE DELIBERATELY-BROKEN INPUTS, NEVER INJECTED DEFECTS
----------------------------------------------------------------------
Per the discriminating-canary doctrine, no production code is mutated to
manufacture a RED here. Every RED is a TRANSPORT or CONFIG that a real Asana
deployment can genuinely present:

  * ``_TruncatingTransport``  — a brim-full page with no continuation token.
    This is exactly the shape S-3 met live: a continuation signal that says
    "complete" over a result set that is not.
  * ``_EmptyTransport``       — a wrong/renamed project gid, or a scope that
    hides every task.
  * ``_FieldlessTransport``   — the custom field not applied to the project.
  * unconfigured option gids  — the pre-flip dark posture.

★ NOTE ON THE TRIPWIRE MODEL
-----------------------------
``_tripwire_verdict`` below is a LOCAL MODEL of the consumer's arithmetic
(``funnel_liveness.evaluate_cross_source_tripwire``, autom8y#1834). The real
consumer lives in a different repository and cannot be imported here, so these
tests prove the census produces an operand that makes the consumer agree or
disagree correctly — they do NOT prove the deployed consumer is wired to this
route. That remains an S-7/PT-04 obligation and is stated as such in the return.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.domain.forwarding_stage import ForwardingStage
from autom8_asana.services.forwarding_stage_census import (
    ASANA_MAX_PAGE_SIZE,
    UNKNOWN_KEY,
    UNSET_KEY,
    StageCensusEmptyCorpus,
    StageCensusError,
    StageCensusFieldAbsent,
    StageCensusTruncated,
    StageCensusUnconfigured,
    census,
)

FIELD_GID = "1216419441591239"
OPTION_GIDS = {
    ForwardingStage.SENT.value: "opt-sent",
    ForwardingStage.APPROVED.value: "opt-approved",
    ForwardingStage.VERIFIED.value: "opt-verified",
    ForwardingStage.STALLED.value: "opt-stalled",
    ForwardingStage.FLOWING.value: "opt-flowing",
    ForwardingStage.LIVE.value: "opt-live",
    ForwardingStage.INACTIVE.value: "opt-inactive",
}


# ---------------------------------------------------------------------------
# Corpus + transport doubles. Each transport is a REAL Asana posture.
# ---------------------------------------------------------------------------


def _task(option_gid: str | None, *, field_present: bool = True) -> dict[str, Any]:
    """One task row as Asana returns it under ``opt_fields=custom_fields``."""
    if not field_present:
        return {"gid": "t", "custom_fields": []}
    enum_value = {"gid": option_gid} if option_gid else None
    return {"gid": "t", "custom_fields": [{"gid": FIELD_GID, "enum_value": enum_value}]}


def _corpus(verified: int = 0, other: int = 0, unset: int = 0) -> list[dict[str, Any]]:
    """A corpus whose TRUE Verified count is ``verified``, by construction."""
    rows = [_task("opt-verified") for _ in range(verified)]
    rows += [_task("opt-live") for _ in range(other)]
    rows += [_task(None) for _ in range(unset)]
    return rows


class _PagingTransport:
    """Faithful Asana pagination over a fixed corpus: pages of <=100 + offsets."""

    def __init__(self, rows: list[dict[str, Any]], page_size: int = ASANA_MAX_PAGE_SIZE):
        self._rows = rows
        self._page_size = page_size
        self.calls: list[dict[str, Any]] = []

    async def get_paginated(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        params = params or {}
        self.calls.append(dict(params))
        start = int(params.get("offset") or 0)
        page = self._rows[start : start + self._page_size]
        nxt = start + self._page_size
        return page, (str(nxt) if nxt < len(self._rows) else None)


class _TruncatingTransport(_PagingTransport):
    """★ THE NAMED TRAP. Returns page 1 and claims there is nothing after it.

    A brim-full page with ``next_offset=None``. This is the S-3 shape verbatim:
    the continuation signal reports completeness over a result set that is not
    complete, and every cheaper check (the page parsed, the rows are well
    formed, the request succeeded) reads identically to a healthy drain.

    NOT a mutation of production code — this is a transport behaviour a real
    upstream can exhibit, which is precisely why the guard against it must be an
    invariant rather than trust in the signal.
    """

    async def get_paginated(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        page, _ = await super().get_paginated(path, params=params)
        return page, None


class _EmptyTransport(_PagingTransport):
    """A wrong/renamed project gid, or a scope that hides every task."""

    def __init__(self) -> None:
        super().__init__([])


class _FieldlessTransport(_PagingTransport):
    """Tasks exist; the Forwarding Stage field is not applied to the project."""

    def __init__(self, n: int = 5) -> None:
        super().__init__([_task(None, field_present=False) for _ in range(n)])


class _ExplodingTransport:
    """Any transport/HTTP failure. Must never surface as an empty census."""

    async def get_paginated(self, path: str, **_: Any) -> tuple[list[dict[str, Any]], str | None]:
        raise TimeoutError("asana timed out")


def _client(transport: Any) -> Any:
    client = MagicMock()
    client._http = MagicMock()
    client._http.get_paginated = AsyncMock(side_effect=transport.get_paginated)
    return client


async def _census(transport: Any, **kwargs: Any):
    return await census(
        _client(transport), field_gid=FIELD_GID, option_gids=dict(OPTION_GIDS), **kwargs
    )


def _tripwire_verdict(*, stage_of_record: int, keyspace: int) -> tuple[str, int]:
    """LOCAL MODEL of funnel_liveness.evaluate_cross_source_tripwire (autom8y#1834).

    Not the deployed consumer (different repo, cannot be imported). Reproduced
    here so the census's operand can be shown to drive AGREE and DISAGREE.
    """
    divergence = stage_of_record - keyspace
    if divergence > 0:
        return "keyspace_undercount", divergence
    if divergence < 0:
        return "keyspace_overcount", divergence
    return ("healthy_zero" if keyspace == 0 else "congruent"), 0


# ===========================================================================
# C-1 — a KNOWN corpus produces a TOTAL, across pages.
# ===========================================================================


@pytest.mark.asyncio
async def test_c1a_green_multi_page_corpus_yields_the_true_total() -> None:
    """GREEN: 7 Verified spread across 3 pages counts as 7, not as page 1's share.

    The corpus is deliberately larger than one Asana page (250 tasks) with the
    Verified rows distributed across all three, so a first-page implementation
    cannot produce the right answer by luck.
    """
    rows = _corpus(verified=3) + _corpus(other=97)  # page 1: 3 verified
    rows += _corpus(verified=2) + _corpus(other=98)  # page 2: 2 verified
    rows += _corpus(verified=2) + _corpus(unset=48)  # page 3: 2 verified
    assert len(rows) == 250

    result = await _census(_PagingTransport(rows))

    assert result.verified_count == 7
    assert result.tasks_scanned == 250
    assert result.pages_drained == 3, "a single-page drain cannot be the total"


@pytest.mark.asyncio
async def test_c1b_green_partition_invariant_makes_the_operand_auditable() -> None:
    """The per-stage buckets SUM to field_present_count.

    Without this, ``verified_count`` is an unaccountable scalar the consumer
    must simply believe. With it, the consumer can check that no clinic was
    lost or double-counted on the way to the number it is about to alarm on.
    """
    rows = _corpus(verified=4, other=6, unset=5)

    result = await _census(_PagingTransport(rows))

    assert sum(result.stage_counts.values()) == result.field_present_count == 15
    assert result.stage_counts[ForwardingStage.VERIFIED.value] == 4
    assert result.stage_counts[UNSET_KEY] == 5


@pytest.mark.asyncio
async def test_c1c_unrecognised_option_is_bucketed_apart_never_as_verified() -> None:
    """An option gid absent from the config map counts as UNKNOWN, not a stage.

    Silently folding an unrecognised option into a known bucket would let a
    workspace-side option rename shift clinics between stages invisibly — and
    Verified is the bucket the tripwire reads. ``read_current_stage`` fails
    closed on this same condition for the same reason.
    """
    rows = _corpus(verified=2) + [_task("opt-RENAMED-BY-OPERATOR")]

    result = await _census(_PagingTransport(rows))

    assert result.verified_count == 2
    assert result.stage_counts[UNKNOWN_KEY] == 1


# ===========================================================================
# C-2 — TWO-SIDED TRIPWIRE TEETH. Agreement AND disagreement.
# ===========================================================================


@pytest.mark.asyncio
async def test_c2a_agree_known_corpus_matches_a_healthy_keyspace() -> None:
    """AGREE: true Verified count 7, keyspace holds 7 -> congruent, divergence 0."""
    rows = _corpus(verified=7, other=40, unset=10)

    result = await _census(_PagingTransport(rows))
    verdict, divergence = _tripwire_verdict(stage_of_record=result.verified_count, keyspace=7)

    assert result.verified_count == 7
    assert verdict == "congruent"
    assert divergence == 0


@pytest.mark.asyncio
async def test_c2b_disagree_a_lost_keyspace_produces_undercount_with_the_right_sign() -> None:
    """DISAGREE: the SAME corpus against a keyspace that lost 3 clinics.

    This is the 2026-07-18 signature reconstructed: the Asana stage of record
    still shows the clinics (the stage never changed — that is why the silence
    was invisible) while the keyspace has been emptied by TTL-reaping and
    delivery-consumption. Sign AND magnitude are asserted: a tripwire that
    disagreed with the wrong sign would point the operator at the wrong system.
    """
    rows = _corpus(verified=7, other=40, unset=10)

    result = await _census(_PagingTransport(rows))
    verdict, divergence = _tripwire_verdict(stage_of_record=result.verified_count, keyspace=4)

    assert verdict == "keyspace_undercount"
    assert divergence == 3


@pytest.mark.asyncio
async def test_c2c_the_two_arms_differ_in_exactly_one_input() -> None:
    """Attribution guard: ONE corpus, two keyspace values, two verdicts.

    C2a and C2b share their census result exactly. If they did not, either
    verdict could be an artifact of a different corpus rather than of the
    difference being measured.
    """
    rows = _corpus(verified=7, other=40, unset=10)
    result = await _census(_PagingTransport(rows))

    agree, _ = _tripwire_verdict(stage_of_record=result.verified_count, keyspace=7)
    disagree, _ = _tripwire_verdict(stage_of_record=result.verified_count, keyspace=4)

    assert agree == "congruent"
    assert disagree == "keyspace_undercount"
    assert agree != disagree


# ===========================================================================
# C-3 — ★ THE NAMED TRAP. Silent truncation is REFUSED, never counted.
# ===========================================================================


@pytest.mark.asyncio
async def test_c3a_red_silent_truncation_refuses_instead_of_counting_page_one() -> None:
    """★ THE KEYSTONE. A brim-full page claiming completeness must REFUSE.

    Broken INPUT: a transport that returns 100 rows with no continuation token
    over a 250-row corpus — S-3's live shape. The true Verified count is 7; page
    one holds only 3.

    Were the census to return 3, the tripwire would read stage-of-record=3
    against a healthy keyspace of 7 and emit ``keyspace_overcount`` — a FALSE
    DISAGREE, pointing the operator at a system that is working. That is worse
    than the silence this whole arc is closing, because it burns the credibility
    of the one instrument that can see the real defect.
    """
    rows = _corpus(verified=3) + _corpus(other=97)
    rows += _corpus(verified=2) + _corpus(other=98)
    rows += _corpus(verified=2) + _corpus(unset=48)

    with pytest.raises(StageCensusTruncated) as excinfo:
        await _census(_TruncatingTransport(rows))

    message = str(excinfo.value)
    assert "brim-full page" in message
    # The refusal is a DETERMINATION, not a guess: the confirmation read found
    # real rows past the offset the signal claimed was the end.
    assert "confirmation read" in message
    assert "silently truncated" in message


@pytest.mark.asyncio
async def test_c3b_green_an_exactly_full_corpus_with_a_real_end_is_not_refused() -> None:
    """GREEN pair for 3a: the guard must not fire on a legitimately-drained set.

    A corpus of exactly 200 (two brim-full pages) where the SECOND page's
    continuation token is genuinely absent because the data genuinely ended.
    Without this arm, 3a would also be satisfied by a census that refused every
    multi-page drain — a guard that never passes is not a guard, it is an outage.
    """
    rows = _corpus(verified=5) + _corpus(other=95) + _corpus(verified=2) + _corpus(unset=98)
    assert len(rows) == 200

    result = await _census(_PagingTransport(rows))

    assert result.verified_count == 7
    # 2 data pages + the confirmation read that PROVED the boundary was real.
    assert result.pages_drained == 3


@pytest.mark.asyncio
async def test_c3c_red_page_ceiling_breach_raises_rather_than_truncating() -> None:
    """RED: a corpus deeper than the ceiling REFUSES; it does not return a prefix.

    Broken INPUT: a runaway corpus against a deliberately low ceiling. The S-3
    posture verbatim — "page ceiling; breach RAISES, never truncates". A count
    over an arbitrary prefix is the wrong number, not a smaller one.
    """
    rows = _corpus(verified=1) + _corpus(other=99)
    rows += _corpus(verified=1) + _corpus(other=99)
    rows += _corpus(verified=1) + _corpus(other=99)

    with pytest.raises(StageCensusTruncated) as excinfo:
        await _census(_PagingTransport(rows), max_pages=2)

    assert "page ceiling" in str(excinfo.value)


@pytest.mark.asyncio
async def test_c3d_green_the_same_corpus_under_a_sufficient_ceiling_counts() -> None:
    """GREEN pair for 3c: identical corpus, adequate ceiling -> the true total.

    Varying ONLY ``max_pages`` flips refusal to a correct count, which is what
    makes 3c attributable to the ceiling rather than to the corpus.
    """
    rows = _corpus(verified=1) + _corpus(other=99)
    rows += _corpus(verified=1) + _corpus(other=99)
    rows += _corpus(verified=1) + _corpus(other=99)

    result = await _census(_PagingTransport(rows), max_pages=10)

    assert result.verified_count == 3


# ===========================================================================
# C-4 — every ambiguous ZERO is a refusal, not a number.
# ===========================================================================


@pytest.mark.asyncio
async def test_c4a_red_empty_corpus_refuses() -> None:
    """RED: zero tasks -> REFUSE. An empty project and a wrong gid are one shape."""
    with pytest.raises(StageCensusEmptyCorpus):
        await _census(_EmptyTransport())


@pytest.mark.asyncio
async def test_c4b_red_field_absent_from_every_task_refuses() -> None:
    """RED: tasks drained, field on none of them -> REFUSE.

    Broken INPUT: the field is not applied to the project (or ``opt_fields``
    did not deliver it). Both read exactly like "no clinic is Verified".
    """
    with pytest.raises(StageCensusFieldAbsent):
        await _census(_FieldlessTransport(n=5))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_gid", "options"),
    [
        ("", OPTION_GIDS),
        (FIELD_GID, {}),
        (FIELD_GID, {ForwardingStage.SENT.value: "opt-sent"}),  # no Verified key
    ],
)
async def test_c4c_red_unconfigured_census_refuses(field_gid: str, options: dict[str, str]) -> None:
    """RED: any missing config half -> REFUSE.

    Boundary analysis on the pre-flip dark posture. An unconfigured census would
    match no task and report 0 Verified with total confidence — the most
    plausible-looking wrong answer this surface can produce.
    """
    with pytest.raises(StageCensusUnconfigured):
        await census(
            _client(_PagingTransport(_corpus(verified=9))),
            field_gid=field_gid,
            option_gids=dict(options),
        )


@pytest.mark.asyncio
async def test_c4d_green_a_genuine_zero_over_a_real_corpus_is_reported() -> None:
    """GREEN: a real corpus where nobody happens to be Verified reports 0.

    The counterweight to all of C-4. A census that refused EVERY zero would be
    unable to report the healthy state the tripwire needs in order to agree —
    ``verified_count == 0`` is legitimate when it is vouched for by a non-empty,
    field-bearing corpus.
    """
    result = await _census(_PagingTransport(_corpus(other=12, unset=3)))

    assert result.verified_count == 0
    assert result.tasks_scanned == 15
    assert result.field_present_count == 15


@pytest.mark.asyncio
async def test_c4e_red_transport_failure_never_becomes_an_empty_census() -> None:
    """RED: a timeout raises inside the taxonomy, never a 0-count success.

    S-3 critic F-6 verbatim: a leaked error "could plausibly be caught somewhere
    as 'no contacts', which is the very ambiguity this surface exists to make
    impossible". Every failure lands inside ``StageCensusError``.
    """
    with pytest.raises(StageCensusError):
        await _census(_ExplodingTransport())


# ===========================================================================
# C-5 — the request the census actually issues.
# ===========================================================================


@pytest.mark.asyncio
async def test_c5_completed_since_is_never_sent() -> None:
    """The drain must NOT filter out completed tasks.

    Asana's ``completed_since`` means "incomplete OR completed since T", so the
    intuitive ``completed_since=now`` would EXCLUDE every completed task and
    silently under-report the total by exactly the population that has finished
    onboarding — the named trap wearing a filter. A completed clinic task still
    carries its stage of record, and the keyspace it is differenced against has
    no completion concept at all, so excluding them would manufacture a
    permanent false DISAGREE.
    """
    transport = _PagingTransport(_corpus(verified=2))

    await _census(transport)

    assert transport.calls, "no request was issued"
    for call in transport.calls:
        assert "completed_since" not in call, f"under-reporting filter sent: {call}"
        assert call["limit"] == ASANA_MAX_PAGE_SIZE
        assert call["opt_fields"] == "custom_fields"
