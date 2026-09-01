"""Wire models for the Forwarding-Stage census read route.

The response is an AGGREGATE surface: counts only. No task gids, no clinic
names, no company ids, no phone numbers. The consumer (the EBI nudge sweep's
cross-source tripwire) needs one number and the means to audit it; it has no
business receiving tenant data, and this service has no business emitting any
across a service boundary for a counting question.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ForwardingStageCensusResponse(BaseModel):
    """A vouched-for census of the Forwarding Stage field.

    Every field present here is a TOTAL over the whole Calendar Integrations
    project. There is no partial-result shape: a census that could not be
    completed is an error response, never a smaller number (see the route's
    error table).
    """

    verified_count: int = Field(
        ...,
        ge=0,
        description=(
            "THE OPERAND. Tasks whose Forwarding Stage is 'Verified' -- the "
            "stage-of-record count the EBI F3 cross-source tripwire differences "
            "against its DynamoDB keyspace. A TOTAL over the project, never a page."
        ),
    )
    tasks_scanned: int = Field(
        ...,
        ge=1,
        description=(
            "Tasks drained from the Calendar Integrations project. The "
            "denominator. Never zero -- a zero-task corpus is refused, because "
            "an empty project and a wrong project gid are indistinguishable "
            "from inside and both would report 0 Verified."
        ),
    )
    field_present_count: int = Field(
        ...,
        ge=1,
        description=(
            "Tasks carrying the Forwarding Stage field definition, set or "
            "unset. Distinct from tasks_scanned on purpose: a task without the "
            "field is out of the census's universe, not a clinic at stage zero."
        ),
    )
    stage_counts: dict[str, int] = Field(
        ...,
        description=(
            "Per-stage counts over the canonical vocabulary plus '__unset__' "
            "(field present, no value) and '__unknown__' (an option gid absent "
            "from the configured map). These values SUM to field_present_count "
            "-- the partition invariant, asserted service-side before this "
            "response is built. It is what makes verified_count auditable by "
            "the consumer rather than an unaccountable scalar."
        ),
    )
    pages_drained: int = Field(
        ...,
        ge=1,
        description=(
            "Pages fetched to produce this census. Present so a consumer can "
            "SEE that a multi-page drain happened, rather than trusting that it "
            "did -- the single most useful signal for detecting a regression "
            "back to first-page semantics."
        ),
    )


__all__ = ["ForwardingStageCensusResponse"]
