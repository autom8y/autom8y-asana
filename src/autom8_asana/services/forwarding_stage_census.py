"""Forwarding-Stage census — the stage-of-record count, or a typed refusal.

READ-ONLY. This module issues ``GET`` requests and counts. It stamps nothing,
claims nothing, and has no write path of any kind.

★ WHY THIS EXISTS
------------------
It is the SECOND OPERAND of the EBI F3 cross-source tripwire (autom8y#1834).
The tripwire differences the EBI DynamoDB ``forwarding|verified`` keyspace
against the DURABLE Asana stage of record, because a count cannot audit itself:
an empty keyspace produced by TTL-reaping, by delivery-consumed rows, and by
genuinely-having-no-stalls all emit the identical healthy-looking
``scanned: 0``. For six weeks a real clinic sat machine-Verified-and-silent
behind exactly that ambiguity.

The Asana Forwarding Stage field is the right second source precisely because it
shares NO failure mode with the keyspace: different service, different store, no
TTL, no claim protocol. It cannot be emptied by either mechanism that emptied the
keyspace. Until this module existed the tripwire could only ever report
``STAGE_OF_RECORD_UNAVAILABLE`` — it could not agree and it could not disagree.

★ THE DEFECT THIS MODULE IS BUILT NOT TO HAVE
----------------------------------------------
**A first-page count dressed as a total.** S-3 was cured of exactly this class
days ago (``CONTRACT-activation-read-surface-2026-09-01.md``): a read that
omitted ``order_by`` + ``include_total`` received ``has_more=False``
unconditionally, so a brim-full page was indistinguishable from a complete
result set — and with no ordering applied the truncated page was an arbitrary,
engine-dependent, non-reproducible slice. One office held 539 candidates against
a 500-row page; 137 leads (1.87%) were being dropped invisibly.

Reintroducing that class HERE would be worse than not building the operand at
all. An under-reporting Verified count makes the tripwire produce a FALSE
DISAGREE, and a tripwire that cries wolf discredits itself faster than one that
stays silent — it would train its reader to ignore the one instrument that can
see the founding defect.

So: **this module returns a TOTAL, or it REFUSES.** There is deliberately no
branch anywhere below that returns a number derived from a partial drain, and no
branch that returns a count it cannot vouch for.

★ THE FIVE REFUSALS, AND WHY EACH IS A REFUSAL RATHER THAN A ZERO
------------------------------------------------------------------
Every one of these would otherwise surface as a perfectly plausible ``0``:

1. ``StageCensusUnconfigured`` — the field GID or the Verified option GID is
   unset. Counting "tasks whose field ``''`` equals option ``''``" yields 0.
2. ``StageCensusEmptyCorpus`` — the drain returned zero tasks. A genuinely empty
   project and a wrong/renamed project GID are indistinguishable from inside,
   and both yield 0.
3. ``StageCensusFieldAbsent`` — tasks were drained but NOT ONE carried the
   Forwarding Stage field definition. Either the field is not applied to this
   project or ``opt_fields`` failed to deliver it; both yield 0.
4. ``StageCensusGidDrift`` — zero Verified matches alongside a non-empty
   unknown bucket: the configured Verified option gid is present but STALE, so
   every genuinely-Verified task fell into UNKNOWN. Yields 0, and it is the
   most dangerous 0 of the five (CENSUS-F-1).
5. ``StageCensusTruncated`` — the drain could not be proven complete (the page
   ceiling was hit). A partial count is a number, and it is the wrong one.

The drain does NOT claim to detect an upstream continuation signal that lies.
Asana emits no total to difference against and its offsets are opaque tokens
that cannot be synthesized, so that detection is not available with the fuel
this API provides; the condition under which it would matter is REPORTED
instead, as ``StageCensus.terminal_page_full`` (CENSUS-F-2).

Doctrine inherited verbatim from the S-3 contract: *"an empty list returned for
a degraded read is indistinguishable from a business that genuinely has no
contacts. That ambiguity IS the trap. Raising makes it structurally
impossible."*
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.project_registry import CALENDAR_INTEGRATIONS_PROJECT
from autom8_asana.domain.forwarding_stage import ForwardingStage

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# The project carrying the Forwarding Stage single-select custom field. Sourced
# from the shared registry, never re-typed here (F-1 single-source lesson).
CI_PROJECT_GID = CALENDAR_INTEGRATIONS_PROJECT

# Asana's maximum page size. Requesting more is silently clamped server-side,
# which is why the absent-fuel invariant below compares against THIS number and
# not against whatever the caller asked for.
ASANA_MAX_PAGE_SIZE = 100

# Page ceiling for one census drain. Breach RAISES, never truncates -- the S-3
# contract's `activation_read_max_pages` posture (`max_pages=20`, "page ceiling;
# breach RAISES, never truncates") and this repo's own `SubtaskPageCapExceeded`
# precedent ("a FULL page cannot prove completeness, so it aborts").
#
# 40 pages x 100 = 4000 CI tasks. The live project holds far fewer, so the
# ceiling is a runaway guard rather than an expected boundary; if it is ever hit
# legitimately, the correct response is to raise it deliberately after looking,
# NOT to let the census quietly report whatever it had managed to read.
DEFAULT_MAX_PAGES = 40


class StageCensusError(RuntimeError):
    """Base: the census could not produce a count it can vouch for.

    Every failure path in this module lands inside this type, so callers route
    on TYPED codes and never on string matching. This mirrors the S-3
    correction, where a bare ``ValueError`` and a leaked token-provider error
    both escaped the taxonomy the consumer routed on -- "a leaked error could
    plausibly be caught somewhere as 'no contacts', which is the very ambiguity
    this surface exists to make impossible."
    """

    code = "STAGE_CENSUS_ERROR"


class StageCensusUnconfigured(StageCensusError):
    """The field GID or the Verified option GID is not configured.

    NOT a zero. With an empty field GID every task fails the match and the
    census would report 0 Verified clinics with total confidence.
    """

    code = "STAGE_CENSUS_UNCONFIGURED"


class StageCensusEmptyCorpus(StageCensusError):
    """The drain returned ZERO tasks from the CI project.

    NOT a zero. A genuinely empty project, a wrong project GID, a renamed or
    archived project, and a permission scope that hides every task are
    indistinguishable from inside -- and all four produce the same empty list.
    The Verified count over an empty corpus is unvouchable by construction.
    """

    code = "STAGE_CENSUS_EMPTY_CORPUS"


class StageCensusFieldAbsent(StageCensusError):
    """Tasks were drained, but NOT ONE carried the Forwarding Stage field.

    NOT a zero. Asana returns the field DEFINITION on every task in a project
    the field is applied to (with ``enum_value: null`` when unset), so a corpus
    with zero occurrences of the field GID means the field is not applied to
    this project, or ``opt_fields`` did not deliver ``custom_fields`` at all.
    Both are configuration defects that read exactly like "no clinic is
    Verified".
    """

    code = "STAGE_CENSUS_FIELD_ABSENT"


class StageCensusGidDrift(StageCensusError):
    """The configured Verified option gid appears STALE (CENSUS-F-1).

    NOT a zero. Zero Verified matches alongside a non-empty unknown bucket is
    the signature of a gid that no longer resolves -- every genuinely-Verified
    task landed in UNKNOWN. The partition invariant cannot see it (UNKNOWN
    absorbs the loss and the buckets still sum), and the unconfigured refusal
    cannot see it (the gid is present, merely wrong).

    Left unrefused this is the WORST output this module can produce: not a
    refusal, not a small error, but a confident ``verified_count=0`` that
    drives a maximal false DISAGREE against a healthy keyspace.
    """

    code = "STAGE_CENSUS_GID_DRIFT"


class StageCensusTruncated(StageCensusError):
    """The drain could not be PROVEN complete. A partial count is refused.

    Raised by two independent guards (see :func:`census`):
      * the page ceiling was reached with a continuation token still pending;
      * the ABSENT-FUEL INVARIANT tripped -- a brim-full page arrived while the
        continuation signal said "no more".

    The second is the load-bearing one. It holds even if the first guard and the
    upstream pagination contract both regress, which is why it is an invariant
    rather than a patch on a symptom (S-3 contract, layer 2).
    """

    code = "STAGE_CENSUS_TRUNCATED"


@dataclass(frozen=True)
class StageCensus:
    """A vouched-for census of the Forwarding Stage field.

    Every field is a scalar or a count. No task gids, no clinic names, no
    company ids -- this is an aggregate surface and carries no tenant data.

    Attributes:
        verified_count: THE OPERAND. Tasks whose Forwarding Stage is Verified.
        tasks_scanned: tasks drained from the CI project. The denominator.
        field_present_count: tasks carrying the field definition (set or unset).
        stage_counts: per-stage counts over the canonical vocabulary, plus
            ``"__unset__"`` (field present, no value) and ``"__unknown__"``
            (an option GID absent from the configured map).
        pages_drained: pages fetched. Present so a consumer can see the drain
            actually happened rather than trusting that it did.
        terminal_page_full: True when the LAST page came back brim-full (at the
            Asana maximum) with no continuation token. That is Asana's
            documented end-of-collection shape AND the shape a silent upstream
            truncation would take, and the two are not separable with the fuel
            Asana provides -- it emits no total to difference against, and a
            synthesized continuation token is unsendable (offsets are opaque
            and must round-trip). So the census ACCEPTS the page and REPORTS
            the condition, rather than manufacturing a detection it cannot
            perform. Steady state is False for all but boundary-aligned
            corpora.

            [UV-P: Asana returns next_page=null (not a token followed by an
            empty page) on a terminal page whose size equals the requested
            limit | METHOD: live GET /tasks against a project whose task count
            is an exact multiple of 100, reading next_page | REASON: not probed
            from this seat; the census fails SAFE either way -- if the
            assumption is wrong the drain under-counts and the tripwire
            DISAGREES loudly rather than silently agreeing, and
            terminal_page_full names every invocation where the assumption was
            load-bearing]

    INVARIANT, asserted before construction: the ``stage_counts`` values sum to
    ``field_present_count``. This makes ``verified_count`` AUDITABLE rather than
    an unaccountable scalar -- a consumer can check the partition itself. A
    count that does not add up is a count nobody can vouch for, which is the
    whole subject of this module.
    """

    verified_count: int
    tasks_scanned: int
    field_present_count: int
    stage_counts: dict[str, int]
    pages_drained: int
    terminal_page_full: bool = False


UNSET_KEY = "__unset__"
"""Field present on the task, no enum value selected (a fresh clinic)."""

UNKNOWN_KEY = "__unknown__"
"""Field carries an option GID absent from the configured map.

Counted separately and NEVER folded into a known stage. Silently bucketing an
unrecognised option would let a workspace-side option rename shift clinics
between stages invisibly -- and the Verified bucket is the one the tripwire
reads. ``read_current_stage`` fails closed on this same condition for the same
reason.
"""


def _stage_for_option_gid(option_gid: str, option_gids: dict[str, str]) -> str:
    """Invert the configured stage->option-GID map. Unrecognised -> UNKNOWN_KEY.

    The inversion direction matches ``ci_task_resolution.read_current_stage``
    exactly: config maps stage value -> option GID, and a read yields an option
    GID that must be looked back up. Re-deriving this differently here would be
    a second source of truth for the same binding.
    """
    for stage_value, configured_gid in option_gids.items():
        if configured_gid == option_gid:
            return stage_value
    return UNKNOWN_KEY


async def census(
    client: AsanaClient,
    *,
    field_gid: str,
    option_gids: dict[str, str],
    project_gid: str = CI_PROJECT_GID,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> StageCensus:
    """Drain the CI project and count Forwarding Stage values. Total, or refuse.

    Args:
        client: the Asana client (PAT-authenticated by the caller).
        field_gid: the Forwarding Stage custom-field DEFINITION gid.
        option_gids: stage value -> enum-option gid, operator-configured. MUST
            contain a ``Verified`` entry -- it is the operand being counted.
        project_gid: the Calendar Integrations project.
        max_pages: page ceiling. Breach RAISES.

    Returns:
        A :class:`StageCensus` whose ``verified_count`` is a TOTAL over the
        whole project, never a page.

    Raises:
        StageCensusUnconfigured: field gid or Verified option gid missing.
        StageCensusEmptyCorpus: the drain returned no tasks.
        StageCensusFieldAbsent: no drained task carried the field.
        StageCensusTruncated: completeness could not be proven.
        StageCensusError: any other degraded read (never an empty result).
    """
    verified_option_gid = (option_gids or {}).get(ForwardingStage.VERIFIED.value, "")
    if not field_gid or not verified_option_gid:
        raise StageCensusUnconfigured(
            "forwarding-stage census refuses: "
            f"field_gid={'set' if field_gid else 'EMPTY'}, "
            f"Verified option gid={'set' if verified_option_gid else 'EMPTY'}. "
            "An unconfigured census would report 0 Verified clinics with total "
            "confidence, which is indistinguishable from a healthy empty funnel."
        )

    stage_counts: dict[str, int] = {stage.value: 0 for stage in ForwardingStage}
    stage_counts[UNSET_KEY] = 0
    stage_counts[UNKNOWN_KEY] = 0

    tasks_scanned = 0
    field_present_count = 0
    pages_drained = 0
    offset: str | None = None
    terminal_page_full = False

    while True:
        if pages_drained >= max_pages:
            # Ceiling reached with a continuation token still pending. RAISE --
            # the alternative is returning a count over an arbitrary prefix of
            # the project, which is precisely the S-3 defect.
            raise StageCensusTruncated(
                f"forwarding-stage census refuses: page ceiling ({max_pages}) "
                f"reached with a continuation token still pending after "
                f"{tasks_scanned} tasks. A count over a partial drain is the "
                "wrong number, not a smaller one."
            )

        rows, next_offset = await _fetch_page(client, project_gid, offset)
        pages_drained += 1

        # ★ CENSUS-F-2 (integrity-architect, BLOCKING) — WHAT USED TO BE HERE,
        # WHY IT WAS WRONG, AND WHAT REPLACES IT.
        #
        # This block previously ran a "confirmation read" whenever a brim-full
        # page arrived with no continuation token, sending a SYNTHESIZED offset
        # (`str(tasks_scanned + len(rows))`) to decide whether the signal lied.
        # That was unsound at the mechanism level: Asana paginates by OPAQUE
        # TOKENS that must round-trip from the API (`models/common.py:102`
        # "next_page.offset"; the transport's own fixture emits `"abc123"` at
        # `tests/unit/transport/test_asana_http.py:199`). An integer index is
        # not a token Asana ever issued, so the confirmation read could not do
        # what it claimed: its accept-branch was unreachable in production and
        # both outcomes collapsed to a generic transport error.
        #
        # Worse, the unit fixture modelled integer indices and called itself
        # "faithful Asana pagination", so the GREEN control certified semantics
        # the live API does not have -- the fixture-encodes-the-premise class,
        # transplanted intact from S-3 iter-1 into the very cure for S-3.
        #
        # THE HONEST POSITION. The S-3 absent-fuel invariant does not transfer
        # here. It was sound against a route whose `has_more` was DEMONSTRABLY
        # miscomputed from `order_by`/`include_total` presence. Asana's
        # `next_page: null` is a different mechanism, and Asana supplies no
        # independent total to difference against -- so "the continuation signal
        # lied" is NOT detectable from inside with the fuel this API provides.
        # Manufacturing a detection for it produced theatre: a guard that looked
        # protective, could not fire, and made an exact-multiple corpus go dark.
        #
        # WHAT IS ENFORCED INSTEAD (both real, both testable):
        #   1. NO FABRICATED FUEL. Every offset sent is one the API itself
        #      emitted; `offset` is only ever `None` or a prior `next_offset`.
        #      The fabrication class is now structurally absent rather than
        #      warned against, and a test asserts every issued offset was
        #      API-issued.
        #   2. THE TRUST IS RECORDED, NOT ASSUMED. A brim-full terminal page is
        #      Asana's documented end-of-collection shape AND the shape a silent
        #      truncation would take. We accept it -- and surface
        #      `terminal_page_full` on the census so the one place the drain
        #      trusts an upstream signal is visible to its consumer instead of
        #      buried. See the UV-P on `StageCensus.terminal_page_full`.
        terminal_page_full = len(rows) >= ASANA_MAX_PAGE_SIZE and next_offset is None

        for row in rows:
            tasks_scanned += 1
            bucket = _classify_row(row, field_gid=field_gid, option_gids=option_gids)
            if bucket is None:
                continue  # field not on this task at all
            field_present_count += 1
            stage_counts[bucket] = stage_counts.get(bucket, 0) + 1

        if next_offset is None:
            break
        offset = next_offset

    if tasks_scanned == 0:
        raise StageCensusEmptyCorpus(
            f"forwarding-stage census refuses: project {project_gid} returned "
            "ZERO tasks. An empty project, a wrong project gid, and a scope "
            "that hides every task are indistinguishable from here, and all "
            "three yield a Verified count of 0."
        )

    if field_present_count == 0:
        raise StageCensusFieldAbsent(
            f"forwarding-stage census refuses: {tasks_scanned} tasks drained "
            f"and NOT ONE carries field {field_gid}. The field is not applied "
            "to this project, or custom_fields were not returned -- both read "
            "exactly like 'no clinic is Verified'."
        )

    # Partition invariant. A census whose buckets do not account for every
    # field-bearing task has lost or double-counted a clinic, and the Verified
    # bucket is the one the tripwire reads.
    bucket_total = sum(stage_counts.values())
    if bucket_total != field_present_count:
        raise StageCensusError(
            "forwarding-stage census refuses: bucket total "
            f"({bucket_total}) != field-present tasks ({field_present_count}). "
            "The partition lost or duplicated a task, so no bucket -- including "
            "Verified -- can be vouched for."
        )

    verified_count = stage_counts[ForwardingStage.VERIFIED.value]
    unknown_count = stage_counts[UNKNOWN_KEY]

    # ★ CENSUS-F-1 (integrity-architect, BLOCKING) — THE GID-DRIFT REFUSAL.
    #
    # The refusals above catch an EMPTY Verified option gid. They do not catch a
    # WRONG one. If the configured Verified gid drifts stale -- an operator
    # re-creates the field, or the option is rebuilt and re-issued -- then every
    # genuinely-Verified task carries an option gid absent from the map, falls
    # into UNKNOWN, and the census returns `verified_count=0` with total
    # confidence. The partition invariant does NOT catch it, because UNKNOWN
    # absorbs the loss and the buckets still sum correctly.
    #
    # The critic's probe: 7 Verified + 13 other, Verified gid drifted ->
    # returned verified_count=0 (truth 7), unknown=7, no refusal. Downstream
    # that is a MAXIMAL keyspace_overcount -- a false DISAGREE against a
    # perfectly healthy keyspace, which is precisely the harm this module's own
    # keystone test names as disqualifying.
    #
    # THE DRIFT SIGNATURE: zero Verified AND a non-empty unknown bucket. A
    # genuinely-zero-Verified project has nothing to misclassify, so unknown
    # would be zero too; the conjunction is what makes this specific rather than
    # a blanket "unknown is bad" rule.
    if verified_count == 0 and unknown_count > 0:
        raise StageCensusGidDrift(
            "forwarding-stage census refuses: ZERO tasks matched the configured "
            f"Verified option gid, but {unknown_count} task(s) carry an option "
            "gid absent from the configured map. That is the signature of a "
            "STALE Verified gid, not of an empty funnel -- returning 0 here "
            "would hand the tripwire a false DISAGREE against a healthy "
            "keyspace. Re-read the workspace's Forwarding Stage option gids "
            "into ASANA_API_FORWARDING_STAGE_OPTION_GIDS."
        )

    logger.info(
        "forwarding_stage_census",
        extra={
            "verified_count": verified_count,
            "tasks_scanned": tasks_scanned,
            "field_present_count": field_present_count,
            "pages_drained": pages_drained,
            "unknown_option_count": unknown_count,
            "terminal_page_full": terminal_page_full,
        },
    )
    if unknown_count:
        # NON-ZERO Verified with a non-empty unknown bucket is NOT refused: it is
        # the legitimate shape of a workspace that gained a stage option the
        # config has not learned yet, and refusing it would take the tripwire
        # down for an additive, harmless workspace edit. It is still a partial
        # blind spot in the operand, so it is reported LOUDLY rather than
        # silently tolerated.
        #
        # DELIBERATELY NOT DECIDED HERE: whether a RATIO (say unknown >
        # verified) should escalate to a refusal. That threshold is judgment
        # about how much unmapped population makes the Verified count
        # untrustworthy, and inventing a number here would be exactly the
        # unvalidated-heuristic move this surface refuses elsewhere. Surfaced
        # for the operator rather than guessed.
        logger.warning(
            "forwarding_stage_census_unmapped_options",
            extra={
                "unknown_option_count": unknown_count,
                "verified_count": verified_count,
                "detail": (
                    "tasks carry Forwarding Stage option gids absent from the "
                    "configured map; the Verified count is a partial view of "
                    "the field until the map is refreshed"
                ),
            },
        )
    return StageCensus(
        verified_count=verified_count,
        tasks_scanned=tasks_scanned,
        field_present_count=field_present_count,
        stage_counts=dict(stage_counts),
        pages_drained=pages_drained,
        terminal_page_full=terminal_page_full,
    )


async def _fetch_page(
    client: AsanaClient, project_gid: str, offset: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch ONE raw page of CI tasks with their custom fields.

    Deliberately uses the raw paginated transport rather than
    ``client.tasks.list_async(...).collect()``. ``PageIterator.collect`` drains
    until the continuation token is exhausted with NO page ceiling and NO
    truncation guard (``models/common.py`` ``_fetch_next_page``), so it can
    neither bound a runaway drain nor detect the absent-fuel condition. Owning
    the loop is what makes both guards expressible.

    Raises:
        StageCensusError: any transport/HTTP failure. NEVER an empty page --
        an error must not be able to masquerade as "this page had no tasks".
    """
    params: dict[str, Any] = {
        "project": project_gid,
        "opt_fields": "custom_fields",
        "limit": ASANA_MAX_PAGE_SIZE,
        # ``completed_since`` is deliberately OMITTED, and the omission is
        # load-bearing. Asana's semantics are "return tasks that are either
        # INCOMPLETE or were completed since this time", so the intuitive-looking
        # `completed_since=now` would EXCLUDE every completed task -- silently
        # under-reporting the total by exactly the population that has finished
        # onboarding. That is the S-3 defect class wearing a filter: a number
        # that looks like a total and is a subset. Omitting the parameter
        # returns complete AND incomplete tasks, which is the true denominator.
        # A completed clinic task still carries its Forwarding Stage, and the
        # EBI keyspace it is differenced against has no completion concept at
        # all -- so excluding them would manufacture a permanent false DISAGREE.
    }
    if offset:
        params["offset"] = offset

    try:
        data, next_offset = await client._http.get_paginated("/tasks", params=params)
    except StageCensusError:
        raise
    except Exception as exc:  # BROAD-CATCH: boundary -- never empty-on-error.
        raise StageCensusError(
            f"forwarding-stage census refuses: task listing failed ({type(exc).__name__}). "
            "A degraded read must never be reported as an absence of clinics."
        ) from exc

    rows = [row for row in (data or []) if isinstance(row, dict)]
    return rows, next_offset


def _classify_row(
    row: dict[str, Any], *, field_gid: str, option_gids: dict[str, str]
) -> str | None:
    """Bucket ONE task by its Forwarding Stage value.

    Returns the bucket key, or ``None`` when the task does not carry the field
    at all (counted in ``tasks_scanned`` but not in ``field_present_count`` --
    the two denominators are deliberately distinct).

    The field-reading shape mirrors ``ci_task_resolution.read_current_stage``:
    match on the field-definition gid, then read ``enum_value.gid``. An absent
    or null ``enum_value`` is UNSET (a fresh clinic), never Verified.
    """
    for custom_field in row.get("custom_fields") or []:
        if not isinstance(custom_field, dict) or custom_field.get("gid") != field_gid:
            continue
        enum_value = custom_field.get("enum_value")
        if not isinstance(enum_value, dict):
            return UNSET_KEY
        option_gid = enum_value.get("gid")
        if not option_gid:
            return UNSET_KEY
        return _stage_for_option_gid(option_gid, option_gids)
    return None


__all__ = [
    "ASANA_MAX_PAGE_SIZE",
    "CI_PROJECT_GID",
    "DEFAULT_MAX_PAGES",
    "UNKNOWN_KEY",
    "UNSET_KEY",
    "StageCensus",
    "StageCensusEmptyCorpus",
    "StageCensusError",
    "StageCensusFieldAbsent",
    "StageCensusGidDrift",
    "StageCensusTruncated",
    "StageCensusUnconfigured",
    "census",
]
