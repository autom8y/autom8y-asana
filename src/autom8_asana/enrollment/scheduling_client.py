"""WS-A PR-3 -- the client for THE GOVERNED WRITE PATH (the only crossing).

Every enrollment write in this lineage goes through ``autom8y-scheduling``'s
``PATCH /api/v1/businesses/{phone}/config`` carrying a SERVICE token whose
``client_id`` is on that service's enrollment-writer allowlist. There is no other
write path in this package: NO direct DB access, NO ``Business()`` (instantiation
WRITES to Asana -- probe scar), NO raw SQL.

Design of record: ``TDD-ws-a-intent-gate-bridge-2026-08-05.md`` §3.4 (idempotent
sync semantics), §4 (the governed write path), §5 (fail-closed EXECUTION).

------------------------------------------------------------------------------
★ OUTCOMES ARE TYPED AND EXHAUSTIVE -- never an exception for an expected 4xx
------------------------------------------------------------------------------
Each call returns a result carrying a bounded :class:`Outcome` plus detail. The
caller CLASSIFIES and COUNTS; it never has to interpret a status code, and no
expected condition arrives as a stack trace. This is what makes the cycle summary
reconcilable (NFR-5: every unresolved office appears in exactly one queue line).

★ ``PREREQ_REFUSED`` is TERMINAL FOR THE CYCLE, NOT AN ERROR. The charter (bulk
grammar) says an office the prereq gate refuses is "refused LOUDLY and queued as
setup work, never force-flipped". So this client:

  * NEVER retries a ``SCHEDULING_ENABLE_REFUSED`` as a flip,
  * NEVER attempts to satisfy the prerequisites itself,
  * NEVER falls back to another write path,

and the caller keeps ``PREREQ_REFUSED`` out of its error budget. Conflating
"correctly refused" with "broken" would train the operator to ignore the signal.

★ ``INVALID_PHONE`` is a REAL class, not defensive padding. The service's
``OfficePhoneField`` carries an E.164 ``pattern``, so a frame phone that is not
E.164 is rejected at validation (422) before any handler logic. The honest
disposition is to COUNT and EMIT it -- never to "fix" it by canonicalizing here.
Canonicalizing would risk FALSE JOINS across distinct offices, which is a silent
wrong-office write; refusing is loud and correct (TDD §3.3, R-1).
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, NamedTuple

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

#: Default base URL of the governed write path.
DEFAULT_SCHEDULING_BASE_URL = "https://scheduling.api.autom8y.io"

#: Route prefix (``app.py`` mounts ``businesses_router`` at ``/api/v1/businesses``).
BUSINESSES_PREFIX = "/api/v1/businesses"

#: ``write_source`` value carried into the service-side receipt.
WRITE_SOURCE = "governed_api"


class Outcome(StrEnum):
    """Bounded, non-PII disposition of one office in one cycle.

    Safe as a CloudWatch metric dimension (never a phone or a guid -- I-NO-PII-METRIC).
    """

    #: The READ leg succeeded -- current gate state is known. Not a disposition in
    #: itself; the caller turns it into NOOP or a delta.
    READ_OK = "read_ok"
    #: Requested state == current state. No call made (client-side delta guard).
    NOOP = "noop"
    #: A real delta the DRY-RUN deliberately did not write. Kept distinct from NOOP
    #: so a dry-run cycle cannot be misread as "already converged" -- these offices
    #: WOULD have been written.
    DRY_RUN_SUPPRESSED = "dry_run_suppressed"
    #: PATCH 200 -- the gate actually moved. A receipt exists iff this happened.
    APPLIED = "applied"
    #: 404 BUSINESS_NOT_FOUND -- no Business row for this phone. Queue, never guess.
    UNRESOLVED = "unresolved"
    #: 404 SCHEDULING_NOT_CONFIGURED -- no business offer. Queue as setup work.
    NOT_CONFIGURED = "not_configured"
    #: 400 SCHEDULING_ENABLE_REFUSED -- prerequisites unmet. LOUD + queued, NOT an error.
    PREREQ_REFUSED = "prereq_refused"
    #: 422 / 400 OFFICE_PHONE_MISMATCH -- the phone is not an acceptable gate key.
    INVALID_PHONE = "invalid_phone"
    #: 401 / 403 -- the guard bit us. The observable side of "the guard BITES".
    WRITE_DENIED = "write_denied"
    #: Read failed (5xx / transport). Current state UNKNOWN -> the office is NOT written.
    READ_FAILED = "read_failed"
    #: Any other non-2xx or transport failure on the write leg.
    ERROR = "error"


#: Outcomes that are CORRECT behaviour, not faults. Excluded from the error budget
#: so a healthy backlog of setup work never reads as an incident.
NON_ERROR_OUTCOMES: frozenset[Outcome] = frozenset(
    {
        Outcome.READ_OK,
        Outcome.NOOP,
        Outcome.DRY_RUN_SUPPRESSED,
        Outcome.APPLIED,
        Outcome.UNRESOLVED,
        Outcome.NOT_CONFIGURED,
        Outcome.PREREQ_REFUSED,
    }
)


class ConfigRead(NamedTuple):
    """Result of ``GET /businesses/{phone}/config``."""

    outcome: Outcome
    #: Current gate state. ``None`` whenever the outcome is not a successful read --
    #: deliberately NOT defaulted to False, because "unknown" and "disabled" must
    #: never be confused (that confusion is how a bridge mass-enables).
    scheduling_enabled: bool | None
    offer_id: int | None
    offer_guid: str | None
    detail: str | None


class ConfigWrite(NamedTuple):
    """Result of ``PATCH /businesses/{phone}/config``."""

    outcome: Outcome
    #: ``reasons[]`` from SCHEDULING_ENABLE_REFUSED -- the queue signal source.
    reasons: tuple[str, ...]
    detail: str | None


def _error_code(body: Any) -> str:
    """Extract ``error.code`` from the scheduling error envelope, or ``""``."""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            return str(error.get("code") or "")
    return ""


def _error_reasons(body: Any) -> tuple[str, ...]:
    """Extract ``error.details.reasons[]`` (the prereq queue signal)."""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            details = error.get("details")
            if isinstance(details, dict):
                reasons = details.get("reasons")
                if isinstance(reasons, list):
                    return tuple(str(r) for r in reasons)
    return ()


def _json_or_none(response: Any) -> Any:
    """Parse a JSON body, tolerating a non-JSON error page without raising."""
    try:
        return response.json()
    except Exception:  # noqa: BLE001 -- a non-JSON body is data, not a control-flow event
        return None


class SchedulingConfigClient:
    """Read + write the enrollment gate through the ONE governed path.

    I/O is confined to this class so the bridge orchestrator stays injectable and
    unit-testable with zero live AWS and zero live HTTP.

    Args:
        http: an object exposing ``get(url, headers=...)`` and
            ``patch(url, json=..., headers=...)`` returning httpx-shaped responses.
            In production this is an ``autom8y_http.SyncHttpClient`` (raw ``httpx``
            is banned by house policy); in tests it is a fake.
        token_provider: returns a fresh service JWT. Called per request so
            TokenManager's own caching/refresh governs the lifetime -- this class
            never caches a credential.
    """

    def __init__(
        self,
        http: Any,
        token_provider: Callable[[], str],
    ) -> None:
        self._http = http
        self._token_provider = token_provider

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token_provider()}",
            "Content-Type": "application/json",
        }

    def get_config(self, office_phone: str) -> ConfigRead:
        """Read the CURRENT gate state for one office.

        ★ On any failure the returned ``scheduling_enabled`` is ``None``, never
        ``False``. An office whose current state cannot be read is UNKNOWN, and the
        caller must not write it -- a write from an unknown baseline is exactly the
        blind mass-change this design refuses.
        """
        url = f"{BUSINESSES_PREFIX}/{office_phone}/config"
        try:
            response = self._http.get(url, headers=self._headers())
        except Exception as exc:  # noqa: BLE001 -- transport failure is a classified outcome
            return ConfigRead(Outcome.READ_FAILED, None, None, None, f"transport: {exc}")

        status = int(response.status_code)
        body = _json_or_none(response)

        if status == 200:
            data = body.get("data", {}) if isinstance(body, dict) else {}
            enabled = data.get("scheduling_enabled")
            if not isinstance(enabled, bool):
                return ConfigRead(
                    Outcome.READ_FAILED,
                    None,
                    None,
                    None,
                    "scheduling_enabled absent or non-boolean in a 200 body",
                )
            offer_id = data.get("offer_id")
            return ConfigRead(
                Outcome.READ_OK,
                enabled,
                offer_id if isinstance(offer_id, int) else None,
                str(data["offer_guid"]) if data.get("offer_guid") else None,
                None,
            )
        if status == 404:
            code = _error_code(body)
            outcome = (
                Outcome.NOT_CONFIGURED
                if code == "SCHEDULING_NOT_CONFIGURED"
                else Outcome.UNRESOLVED
            )
            return ConfigRead(outcome, None, None, None, code or "404")
        if status in (401, 403):
            return ConfigRead(
                Outcome.WRITE_DENIED, None, None, None, _error_code(body) or str(status)
            )
        if status == 422:
            return ConfigRead(Outcome.INVALID_PHONE, None, None, None, "422 phone validation")
        return ConfigRead(Outcome.READ_FAILED, None, None, None, f"http {status}")

    def set_scheduling_enabled(
        self,
        office_phone: str,
        *,
        scheduling_enabled: bool,
        intent_source: str,
    ) -> ConfigWrite:
        """Write the gate for one office. DELTA-ONLY -- the caller has already
        established that this is a real state change.

        ``office_phone`` is sent in BOTH the path and the body: the service
        enforces coherence (400 ``OFFICE_PHONE_MISMATCH``), which closes the
        silent-ignore wart where the body value was required but never read.

        ``intent_source`` is carried purely so the service-side
        ``scheduling_config_updated`` receipt can distinguish an explicitly-set
        intent from one coerced from UNSET. It never influences the write.
        """
        url = f"{BUSINESSES_PREFIX}/{office_phone}/config"
        payload = {
            "office_phone": office_phone,
            "scheduling_enabled": scheduling_enabled,
            "intent_source": intent_source,
        }
        try:
            response = self._http.patch(url, json=payload, headers=self._headers())
        except Exception as exc:  # noqa: BLE001 -- transport failure is a classified outcome
            return ConfigWrite(Outcome.ERROR, (), f"transport: {exc}")

        status = int(response.status_code)
        body = _json_or_none(response)

        if status == 200:
            return ConfigWrite(Outcome.APPLIED, (), None)
        if status == 400:
            code = _error_code(body)
            if code == "SCHEDULING_ENABLE_REFUSED":
                # ★ TERMINAL for this office this cycle. NOT retried as a flip, NOT
                # remediated here, NOT an error. The reasons ARE the queue.
                return ConfigWrite(Outcome.PREREQ_REFUSED, _error_reasons(body), code)
            if code == "OFFICE_PHONE_MISMATCH":
                return ConfigWrite(Outcome.INVALID_PHONE, (), code)
            return ConfigWrite(Outcome.ERROR, (), code or "400")
        if status == 404:
            code = _error_code(body)
            outcome = (
                Outcome.NOT_CONFIGURED
                if code == "SCHEDULING_NOT_CONFIGURED"
                else Outcome.UNRESOLVED
            )
            return ConfigWrite(outcome, (), code or "404")
        if status in (401, 403):
            return ConfigWrite(Outcome.WRITE_DENIED, (), _error_code(body) or str(status))
        if status == 422:
            return ConfigWrite(Outcome.INVALID_PHONE, (), "422 phone validation")
        return ConfigWrite(Outcome.ERROR, (), f"http {status}")


__all__ = [
    "BUSINESSES_PREFIX",
    "DEFAULT_SCHEDULING_BASE_URL",
    "NON_ERROR_OUTCOMES",
    "WRITE_SOURCE",
    "ConfigRead",
    "ConfigWrite",
    "Outcome",
    "SchedulingConfigClient",
]
