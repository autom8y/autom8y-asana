"""Receipt schema for RUNG E limb (a) of the asana-native-insight-delivery telos.

EX-4 of the exec-insight-delivery wave (shape
``.sos/wip/frames/exec-insight-delivery.shape.md`` §EX-4, L300-348).

What limb (a) IS
----------------
RUNG E is the *exec-phase* bar added to the telos by operator ruling R-15
(``.ledge/decisions/RULING-operator-morning-set-2026-08-13.md:148-160``). The
telos splits RUNG E into three limbs; **only limb (a) is mechanically
attestable** (the telos's own attester split,
``.know/telos/asana-native-insight-delivery.md:171-183``): limbs (b)/(c) are
felt observations closed by the operator alone and NO agent — including the
seat that drafted the rung — may close them.

Limb (a)'s shape (NOT put in question by R-15, so buildable ahead of Q-1):

    two delivery occurrences, each with a generation receipt,
    jointly showing NO HUMAN assembled either.

This module is the durable, queryable **join contract** that makes that shape
observable: it joins a *delivery* occurrence (the payload reached the channel)
to its *generation* provenance (the payload was machine-assembled, no human in
the loop), keyed on ``invocation_id``.

Why a JOIN and not a single event (the founding finding, NR-4)
--------------------------------------------------------------
The delivery half already exists and is LIVE. The autom8y ASR service
(``services/account-status-recon``) emits, per scheduled tick
(``cron(0 */4 * * ? *)`` = 6/day), a real chain

    slack_post_entered -> slack_post_attempt -> report_posted

on ``#account-health``. ``report_posted`` is a genuine *delivery* event (it
sits after the wire call and cannot fire under ``dry_run`` or on Slack
``ok:false`` -- established at ``CRITIQUE-s3-delivery-rails-2026-08-12.md``
§5.1). An own-hands read-only CloudWatch Logs Insights census over
``/aws/lambda/autom8y-account-status-recon`` (2026-08-13, queryId
``7c59f3d8-821c-4b47-9034-f5d02a3d3fc8``, 57 rows / 15 invocations) confirmed
those deliveries now carry **real readouts** (``block_count: 42``,
``abort_reason: report_success``, ``text_preview`` naming findings), not only
3-block aborts.

BUT: the same census queried ``report_generated`` and returned **zero rows**.
No event attests *authorship* of the delivered payload. ``report_posted``
fires identically whether the 42 blocks were machine-assembled by the
generation pipeline or hand-pasted by an operator through the same
``send_blocks`` egress. Limb (a)'s "no human assembled either" is therefore
**un-observable from delivery telemetry alone** -- the generation-provenance
receipt that would carry it does not exist, and nothing joins it to delivery.

So the founding negative NARROWS (it does not stand as "nothing emits", which
would be false): *no generation-provenance receipt exists, joinable to the live
``report_posted`` delivery receipt on ``invocation_id``, attesting the payload
was machine-assembled.* This schema therefore **builds on** the live delivery
chain and **defines the missing generation half** plus the join binding them.

The generation-event contract (``report_generated``) below is a
platform-behavior claim about a NOT-YET-SHIPPED primitive (the EX-5 generation
path). Per structural-verification-receipt §6 / AP-4 it is labelled UV-P and is
NOT asserted as present:

    [UV-P: the ASR readout generation path emits a report_generated
    provenance event carrying assembled_by/human_in_loop/content_hash keyed on
    invocation_id | METHOD: deferred-to-EX-5-application | REASON: report.py's
    block-assembly path emits no such event today; own-hands census
    queryId 7c59f3d8-821c-4b47-9034-f5d02a3d3fc8 returned zero report_generated
    rows. EX-5 (WS-2 generation mechanism) is the discharge site.]

FS-5 -- the two ladders must stay separably observable
------------------------------------------------------
R-15's fence: the exec rung does NOT substitute for rung 4, and neither may be
graded in place of the other. This schema enforces that structurally: every
occurrence receipt carries a ``rung_4_attestation`` line AND a
``rung_e_limb_a_attestation`` line as **independent siblings**. This module
sets ONLY the rung-E line, from delivery+generation telemetry. It NEVER sets
the rung-4 line -- rung 4 is felt/operator-only and MUST NOT be inferred from
delivery or generation signals. There is deliberately NO combined /
"engagement" / total field: a combined metric would collapse the two ladders
and break the fence (shape §EX-4 "must not: emit a combined engagement
metric").
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum


class DeliveryOutcome(StrEnum):
    """Delivery-side classification, read straight off ``report_posted``.

    This is a property of the *delivery*, never of authorship. ``READOUT`` is
    NOT a generation receipt -- it only means the tick did not abort. See the
    module docstring: ``report_posted`` is silent on who assembled the blocks.
    """

    READOUT = "readout"  # abort_reason == report_success
    ABORT = "abort"  # abort_reason == readiness_gate_abort
    OTHER = "other"


class Assembler(StrEnum):
    """Who assembled the delivered payload (generation-side)."""

    MACHINE = "machine"
    HUMAN = "human"
    UNKNOWN = "unknown"


class RungEObservability(StrEnum):
    """Mechanical status of RUNG E limb (a) for a single occurrence."""

    OBSERVABLE = "observable"  # delivery + machine-generation, no human in loop
    NOT_OBSERVABLE = "not_observable"  # with a machine-readable reason


class Rung4Status(StrEnum):
    """RUNG 4 (acted-on) status -- felt, operator-only.

    This schema NEVER moves this off ``UNATTESTED_FELT_OPERATOR_ONLY``. It
    exists so the two ladders are separably observable (FS-5); it is a
    deliberate sentinel, not a value this instrument computes.
    """

    UNATTESTED_FELT_OPERATOR_ONLY = "unattested_felt_operator_only"


class NotObservableReason(StrEnum):
    """Why an occurrence is not RUNG-E-limb-(a)-observable."""

    GENERATION_PROVENANCE_ABSENT = "generation_provenance_absent"
    HUMAN_IN_LOOP = "human_in_loop"
    ASSEMBLED_BY_HUMAN = "assembled_by_human"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    NOT_DELIVERED = "not_delivered"


class LimbAStatus(StrEnum):
    """Aggregate limb (a) status across occurrences."""

    SATISFIED = "satisfied"  # >= 2 occurrences each RUNG-E-observable
    NOT_YET_OBSERVED = "not_yet_observed"


# The event name the delivery chain terminates at, in ASR
# (services/account-status-recon/src/account_status_recon/orchestrator.py:1251,
# per CRITIQUE-s3-delivery-rails-2026-08-12.md §5.1). Delivery half: LIVE.
DELIVERY_EVENT = "report_posted"

# The generation-provenance event this contract defines. NOT-YET-EMITTED
# (UV-P, see module docstring): EX-5's generation path is the discharge site.
GENERATION_EVENT = "report_generated"

# Number of distinct RUNG-E-observable occurrences limb (a) requires.
LIMB_A_REQUIRED_OCCURRENCES = 2


@dataclass(frozen=True)
class DeliveryReceipt:
    """The delivery half -- built from the live ``report_posted`` event.

    ``message_ts``/``permalink`` are the DEFER-S-5 durable locator ("durable in
    Slack history and quotable by permalink",
    ``RAILS-insight-delivery-verified-2026-08-12.md:960``). They are OPTIONAL
    here because the live ``report_posted`` event does NOT currently emit a
    Slack message ts -- recorded as a gap the delivery emitter should close, not
    papered over.
    """

    invocation_id: str
    channel: str
    block_count: int
    delivered_at: str
    outcome: DeliveryOutcome
    trace_id: str | None = None
    message_ts: str | None = None
    permalink: str | None = None

    @staticmethod
    def from_event(evt: dict[str, object]) -> DeliveryReceipt:
        """Project a raw ``report_posted`` log event into a delivery receipt."""
        abort_reason = evt.get("abort_reason")
        if abort_reason == "report_success":
            outcome = DeliveryOutcome.READOUT
        elif abort_reason == "readiness_gate_abort":
            outcome = DeliveryOutcome.ABORT
        else:
            outcome = DeliveryOutcome.OTHER
        return DeliveryReceipt(
            invocation_id=str(evt["invocation_id"]),
            channel=str(evt.get("channel", "")),
            block_count=_as_int(evt.get("block_count", 0)),
            delivered_at=str(evt.get("timestamp", "")),
            outcome=outcome,
            trace_id=_opt_str(evt.get("trace_id")),
            message_ts=_opt_str(evt.get("message_ts")),
            permalink=_opt_str(evt.get("permalink")),
        )


@dataclass(frozen=True)
class GenerationReceipt:
    """The generation half -- the ``report_generated`` provenance contract.

    UV-P: NOT emitted by any live surface today (module docstring). This is the
    contract EX-5's generation path must satisfy so limb (a) becomes
    observable. ``human_in_loop`` / ``assembled_by`` are the load-bearing
    "no human assembled it" fields; ``content_hash`` binds the generated
    artifact to the delivered one so a swap cannot pass.
    """

    invocation_id: str
    assembled_by: Assembler
    human_in_loop: bool
    generator: str
    generator_version: str
    source_query_id: str
    content_hash: str
    block_count: int
    generated_at: str

    @staticmethod
    def from_event(evt: dict[str, object]) -> GenerationReceipt:
        """Project a raw ``report_generated`` log event into a generation receipt."""
        raw_assembler = str(evt.get("assembled_by", "unknown"))
        try:
            assembler = Assembler(raw_assembler)
        except ValueError:
            assembler = Assembler.UNKNOWN
        return GenerationReceipt(
            invocation_id=str(evt["invocation_id"]),
            assembled_by=assembler,
            human_in_loop=bool(evt.get("human_in_loop", True)),
            generator=str(evt.get("generator", "")),
            generator_version=str(evt.get("generator_version", "")),
            source_query_id=str(evt.get("source_query_id", "")),
            content_hash=str(evt.get("content_hash", "")),
            block_count=_as_int(evt.get("block_count", 0)),
            generated_at=str(evt.get("generated_at", "")),
        )


@dataclass(frozen=True)
class DeliveryOccurrenceReceipt:
    """One tick: a delivery joined to its generation provenance on invocation_id.

    Carries the two ladders as INDEPENDENT siblings (FS-5). This schema sets
    ``rung_e_limb_a_attestation`` from the join; it fixes ``rung_4_attestation``
    at the operator-only sentinel and never derives it from telemetry.
    """

    invocation_id: str
    delivery: DeliveryReceipt | None
    generation: GenerationReceipt | None
    # --- ladder 1: the exec rung, limb (a) -- mechanically set here ---
    rung_e_limb_a_attestation: RungEObservability
    rung_e_not_observable_reason: NotObservableReason | None
    # --- ladder 2: rung 4 (acted-on) -- felt, NEVER set from telemetry ---
    rung_4_attestation: Rung4Status = Rung4Status.UNATTESTED_FELT_OPERATOR_ONLY

    def to_dict(self) -> dict[str, object]:
        """Durable, JSON-serialisable form of the receipt."""
        out = asdict(self)
        # asdict already coerced nested dataclasses; coerce enums to values.
        result: dict[str, object] = json.loads(json.dumps(out, default=_enum_default))
        return result


@dataclass(frozen=True)
class LimbAObservation:
    """Aggregate limb (a) verdict across a window of occurrence receipts.

    ``status`` is SATISFIED iff at least ``LIMB_A_REQUIRED_OCCURRENCES`` DISTINCT
    invocations are each RUNG-E-observable. The rung-4 ladder is carried
    alongside, always at the operator-only sentinel, so a consumer reading this
    object sees both ladders and cannot mistake one for the other (FS-5).
    """

    status: LimbAStatus
    observable_occurrences: int
    required_occurrences: int
    observable_invocation_ids: list[str]
    receipts: list[DeliveryOccurrenceReceipt] = field(default_factory=list)
    rung_4_attestation: Rung4Status = Rung4Status.UNATTESTED_FELT_OPERATOR_ONLY

    def to_dict(self) -> dict[str, object]:
        """Durable, JSON-serialisable form of the observation."""
        return {
            "rung_e_limb_a": {
                "status": self.status.value,
                "observable_occurrences": self.observable_occurrences,
                "required_occurrences": self.required_occurrences,
                "observable_invocation_ids": list(self.observable_invocation_ids),
                "receipts": [r.to_dict() for r in self.receipts],
            },
            # Sibling ladder -- carried, never collapsed into the above.
            "rung_4": {
                "status": self.rung_4_attestation.value,
                "note": (
                    "felt; operator-only; MUST NOT be derived from delivery or "
                    "generation telemetry (R-15 non-substitution fence)"
                ),
            },
        }


def _opt_str(value: object) -> str | None:
    """Coerce an optional log-event field to ``str | None``."""
    return None if value is None else str(value)


def _as_int(value: object, default: int = 0) -> int:
    """Coerce a log-event field to ``int``, tolerating strings and absence."""
    if isinstance(value, bool):  # bool is an int subclass; keep it explicit
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _enum_default(obj: object) -> str:
    if isinstance(obj, Enum):
        return str(obj.value)
    raise TypeError(f"not JSON serialisable: {type(obj)!r}")


# --- production ingestion queries (CloudWatch Logs Insights) ---------------
#
# The join is fed by two read-only Logs Insights queries over
# /aws/lambda/autom8y-account-status-recon. The delivery query is LIVE today;
# the generation query returns zero rows until EX-5 ships report_generated
# (UV-P, module docstring).

DELIVERY_LOGS_INSIGHTS_QUERY = (
    "fields @timestamp, invocation_id, channel, block_count, abort_reason, "
    "trace_id, message_ts, permalink "
    '| filter event = "report_posted" '
    "| sort @timestamp asc"
)

GENERATION_LOGS_INSIGHTS_QUERY = (
    "fields @timestamp, invocation_id, assembled_by, human_in_loop, generator, "
    "generator_version, source_query_id, content_hash, block_count, generated_at "
    '| filter event = "report_generated" '
    "| sort @timestamp asc"
)


# --- portable wire contract (JSON Schema, draft 2020-12) -------------------
#
# The durable, queryable receipt an attester (eunomia verification-auditor)
# consumes. Kept in lockstep with the dataclasses above.

RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://autom8y.dev/schemas/rung-e-limb-a-receipt.json",
    "title": "RUNG E limb (a) delivery-occurrence receipt",
    "type": "object",
    "required": [
        "invocation_id",
        "delivery",
        "generation",
        "rung_e_limb_a_attestation",
        "rung_4_attestation",
    ],
    "properties": {
        "invocation_id": {"type": "string", "description": "join key"},
        "delivery": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "required": [
                        "invocation_id",
                        "channel",
                        "block_count",
                        "delivered_at",
                        "outcome",
                    ],
                    "properties": {
                        "invocation_id": {"type": "string"},
                        "channel": {"type": "string"},
                        "block_count": {"type": "integer"},
                        "delivered_at": {"type": "string"},
                        "outcome": {"enum": ["readout", "abort", "other"]},
                        "trace_id": {"type": ["string", "null"]},
                        "message_ts": {"type": ["string", "null"]},
                        "permalink": {"type": ["string", "null"]},
                    },
                },
            ]
        },
        "generation": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "required": [
                        "invocation_id",
                        "assembled_by",
                        "human_in_loop",
                        "content_hash",
                    ],
                    "properties": {
                        "invocation_id": {"type": "string"},
                        "assembled_by": {"enum": ["machine", "human", "unknown"]},
                        "human_in_loop": {"type": "boolean"},
                        "generator": {"type": "string"},
                        "generator_version": {"type": "string"},
                        "source_query_id": {"type": "string"},
                        "content_hash": {"type": "string"},
                        "block_count": {"type": "integer"},
                        "generated_at": {"type": "string"},
                    },
                },
            ]
        },
        # --- FS-5: two ladders as independent siblings, never collapsed ---
        "rung_e_limb_a_attestation": {"enum": ["observable", "not_observable"]},
        "rung_e_not_observable_reason": {
            "type": ["string", "null"],
            "enum": [
                "generation_provenance_absent",
                "human_in_loop",
                "assembled_by_human",
                "content_hash_mismatch",
                "not_delivered",
                None,
            ],
        },
        "rung_4_attestation": {
            "enum": ["unattested_felt_operator_only"],
            "description": (
                "felt; operator-only. MUST NOT be derived from delivery or "
                "generation telemetry. Present so the two ladders stay "
                "separably observable (FS-5 / R-15 non-substitution fence)."
            ),
        },
    },
    # There is deliberately NO combined/engagement/total property: such a field
    # would collapse the two ladders and break the R-15 fence.
    "additionalProperties": False,
}
