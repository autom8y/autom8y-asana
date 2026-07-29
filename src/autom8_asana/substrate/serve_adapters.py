"""Substrate-v2 Seam 4 — thin consumer ADAPTERS (DARK; CP-1..6). RC-C(serve) / DP-3.

Per [H18] adapters are THIN: each translates a ``ServedNumber`` to its surface and
holds NO freshness logic (the gate lives in the reader — ``substrate.serve``). Every
path consumes the frozen ``ServedNumber`` sum through an EXHAUSTIVE ``match`` with
``assert_never`` ([H15]) — a bare attribute access on an un-handled arm is a mypy
error — so a consumer CANNOT obtain a value without handling ``Refused``.

DARK build: these are v2-side adapters. NO v1 file is edited and NO consumer is
repointed (cutover is S8; DP-1F HOLD-P6 binds). CP-1..6 route through the
``SubstrateReader`` choke-point BY CONSTRUCTION — a wrapper HOLDS a ``SubstrateReader``
and a translator CONSUMES a ``ServedNumber``; none imports ``store.read_current`` /
``load_dataframe`` (the [H17] raw-read privacy tooth, asserted structurally).

Cross-process contract (DP-3 §Ratification): every ``Refused`` crosses the wire as a
**non-2xx** — ``424 Failed Dependency`` (a dependency's state is unprovable;
non-retry-coded by default) + ``Retry-After`` bound to the rebuild schedule
(parameterized). NO ``Refused`` is ever a 200 — the confidence-labelled stale-200 of
the SUPERSEDED ``ADR-serve-stale-within-bound`` is unconstructable here. Refusal
bodies are SHAPE-HOSTILE (DP-3 §B): no ``rows`` / aggregate / ``value`` / ``data``
field, so a status-ignoring client parses a refusal, not an empty success.

Security posture: refusal bodies carry the LOGICAL plane label + ages + the
caller-supplied reason only — never an S3 key/bucket/version/path. All data-integrity
refusals share ONE status (424), so the surface is not a status oracle; an unknown /
non-servable ``entity_type`` is a CLIENT error at the boundary (the caller's own
input), distinct from the 424 data-integrity class, and reveals no other resource.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, assert_never

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.identity import ArtifactId, artifact_key, is_servable
from autom8_asana.substrate.serve import Provable, Refused, RefuseReason

if TYPE_CHECKING:
    from collections.abc import Mapping

    from autom8_asana.substrate.serve import ServedNumber, SubstrateReader


# ============================================================ CP-1 — CLI ======

# Non-zero DATA-INTEGRITY exit for a refused number (RC-acceptance :104: "a
# DATA-INTEGRITY non-zero exit on the CLI"). Distinct from generic error(1)/usage(2).
DATA_INTEGRITY_EXIT_CODE: int = 3
SERVE_OK_EXIT_CODE: int = 0


@dataclass(frozen=True, slots=True)
class CliServeResult:
    """A CLI outcome: an exit code, a message, and the provable frame bytes (or None).

    ``frame`` is None on refusal — the CLI never prints a fake number (shape-hostile:
    a scripting caller that greps stdout for a dollar figure finds none on a refusal).
    """

    exit_code: int
    message: str
    frame: bytes | None


def serve_result_to_cli(served: ServedNumber) -> CliServeResult:
    """CP-1: map a served number to a CLI (exit_code, message, frame).

    A ``Refused`` → non-zero DATA-INTEGRITY exit + a reason message carrying NO served
    number; a ``Provable`` → exit 0 + the frame. Generalizes v1's single-path
    ``PlaneDivergenceError`` guard (caught only at ``metrics/__main__.py``) to ALL
    reasons via the one choke-point.
    """
    match served:
        case Provable(frame=frame):
            return CliServeResult(exit_code=SERVE_OK_EXIT_CODE, message="provable", frame=frame)
        case Refused(reason=reason):
            return CliServeResult(
                exit_code=DATA_INTEGRITY_EXIT_CODE,
                message=f"DATA-INTEGRITY: substrate refused ({reason.value}); no provable number",
                frame=None,
            )
        case _:
            assert_never(served)


class OfflineServeAdapter:
    """CP-1: offline / CLI read through the choke-point.

    Holds a ``SubstrateReader``; ``serve_cli`` is ``read()`` + ``serve_result_to_cli``.
    There is no mtime path and no per-call-site plane guard — the reader's gate is the
    only verdict.
    """

    def __init__(self, reader: SubstrateReader) -> None:
        self._reader = reader

    async def serve_cli(self, aid: ArtifactId) -> CliServeResult:
        return serve_result_to_cli(await self._reader.read(aid))


# ================================================ CP-2 — force-warm recheck ====


class RecheckOutcome(Enum):
    """A force-warm recheck verdict — derived from is_provable (via the reader), NOT mtime."""

    PROVABLE = "provable"
    REFUSED = "refused"


def serve_result_to_recheck(served: ServedNumber) -> RecheckOutcome:
    """CP-2 translation: ``Provable`` → PROVABLE; any ``Refused`` → REFUSED.

    The distinctive v2 property vs v1's ``from_s3_resolved`` mtime path: the verdict is
    the reader's is_provable verdict ([H16]), so a non-provable recheck REFUSES — never
    a fresh-mtime lie over stale content.
    """
    match served:
        case Provable():
            return RecheckOutcome.PROVABLE
        case Refused():
            return RecheckOutcome.REFUSED
        case _:
            assert_never(served)


class ForceWarmRecheckAdapter:
    """CP-2: force-warm recheck through the choke-point (is_provable, not mtime)."""

    def __init__(self, reader: SubstrateReader) -> None:
        self._reader = reader

    async def recheck(self, aid: ArtifactId) -> RecheckOutcome:
        return serve_result_to_recheck(await self._reader.read(aid))


# =========================================== CP-3/4/5 — service / MCP query ====

# 424 Failed Dependency (DP-3 §Ratification sub-decision 1): STALE/CORRUPT/MISSING/
# DIVERGENT → this non-2xx (the request failed because a dependency's state is
# unprovable), non-retry-coded by default + Retry-After bound to the rebuild schedule.
HTTP_STATUS_REFUSED: int = 424
HTTP_STATUS_OK: int = 200
# An unknown / non-servable entity_type is a CLIENT error at the boundary (bad input),
# NOT a data-integrity refusal — a distinct 422, so the two are never conflated.
HTTP_STATUS_UNSERVABLE_ENTITY: int = 422

_REASON_CODE_PREFIX = "SUBSTRATE_REFUSED_"


def refusal_reason_code(reason: RefuseReason) -> str:
    """Machine-readable wire code for a refusal reason (``SUBSTRATE_REFUSED_STALE`` …)."""
    return f"{_REASON_CODE_PREFIX}{reason.value.upper()}"


@dataclass(frozen=True, slots=True)
class HttpServeResult:
    """An HTTP outcome: status, a body dict, response headers, and the frame (or None).

    Refused → 424 + Retry-After + a SHAPE-HOSTILE ``body`` (no data field) + ``frame``
    None. Provable → 200 + a minimal provenance body + the ``frame`` bytes. A
    status-ignoring client that reads ``frame`` gets None on refusal and MUST inspect
    ``status_code``; one that parses ``body`` for ``rows`` / a value gets a refusal
    envelope, not empty success.
    """

    status_code: int
    body: Mapping[str, Any]
    headers: Mapping[str, str]
    frame: bytes | None


def _refusal_envelope(refused: Refused) -> dict[str, Any]:
    """A SHAPE-HOSTILE refusal body (DP-3 §B): NO data-shaped field.

    No ``rows``, no ``value``/``aggregate``/``data``. Carries the refusal marker, the
    machine-readable reason/code, and the OQ-1 explanation observables (plane, per-copy
    ages, divergence magnitude, per-section delta) + the C13 ``sunset_breach`` marker
    when present. Security: the plane is a logical label and the ages are the caller's
    own artifact's — no S3 path / bucket / version.
    """
    payload = refused.detail
    body: dict[str, Any] = {
        "substrate_refused": True,  # unmistakable refusal marker — NOT a data field
        "reason": refused.reason.value,
        "code": refusal_reason_code(refused.reason),
        "plane": payload.plane,
        "absolute_age_seconds": dict(payload.absolute_age),
        "divergence_magnitude": payload.magnitude,
        "per_section_delta": dict(payload.per_section_delta),
    }
    if payload.sunset_breach is not None:
        breach = payload.sunset_breach
        # C13: the surface-lifecycle breach marker (reason stays STALE; this is the
        # machine-distinguishable RC-D-2 observable at the payload level).
        body["sunset_breach"] = {
            "surface": breach.surface,
            "sunset_after": breach.sunset_after.isoformat(),
            "observed_at": breach.observed_at.isoformat(),
        }
    return body


def serve_result_to_http(served: ServedNumber, *, retry_after_seconds: int) -> HttpServeResult:
    """CP-3/4/5: map a served number to an HTTP result.

    Every ``Refused`` → 424 Failed Dependency + ``Retry-After: {retry_after_seconds}``
    (bound to the rebuild schedule; parameterized) + a shape-hostile body. ``Provable``
    → 200 + the frame. NO code path yields a 200 for a ``Refused`` — the two-sided
    invariant (the SUPERSEDED stale-200 paradigm is unconstructable).
    """
    match served:
        case Provable(frame=frame):
            return HttpServeResult(
                status_code=HTTP_STATUS_OK,
                body={"substrate_provable": True},
                headers={},
                frame=frame,
            )
        case Refused() as refused:
            return HttpServeResult(
                status_code=HTTP_STATUS_REFUSED,
                body=_refusal_envelope(refused),
                headers={"Retry-After": str(retry_after_seconds)},
                frame=None,
            )
        case _:
            assert_never(served)


def coerce_entity_type(raw: str) -> EntityType | None:
    """CP-3/4 boundary: str→EntityType coerce-OR-refuse ([H4]).

    A malformed OR non-servable string → ``None`` (the caller REFUSES — never a silent
    legacy default). Servability reuses the identity registry-derived guard (single
    source), so the servable world follows the registry, not a second drift-prone enum.
    ``EntityType.UNKNOWN`` and structural PROJECT/SECTION coerce to ``None``.
    """
    try:
        candidate = EntityType(raw)
    except ValueError:
        return None
    return candidate if is_servable(candidate) else None


def artifact_cache_key(aid: ArtifactId) -> str:
    """CP-5: the shared ``DataFrameCache`` key DERIVED from ArtifactId, never a bare str.

    A plane-blind cache key is unconstructable — the key is a pure function of the
    typed (project, servable-entity) address (``artifact_key``), so the memory→S3 tier
    the MCP paths resolve through cannot be poisoned by an entity-blind key.
    """
    return artifact_key(aid)


class QueryServeAdapter:
    """CP-3/4/5: the service / MCP query path through the choke-point.

    Coerces the raw URL ``entity_type`` at the boundary (coerce-or-refuse), builds a
    typed ``ArtifactId`` (plane-blindness unconstructable), reads through the reader,
    and maps the ``ServedNumber`` to an HTTP result. An unknown/non-servable entity is
    a 422 client error; a malformed ``project_gid`` (ArtifactId guard) is likewise a
    422 — both distinct from the 424 data-integrity refusal.
    """

    def __init__(self, reader: SubstrateReader) -> None:
        self._reader = reader

    async def query(
        self, project_gid: str, entity_type_raw: str, *, retry_after_seconds: int
    ) -> HttpServeResult:
        entity_type = coerce_entity_type(entity_type_raw)
        if entity_type is None:
            return self._unservable_entity(entity_type_raw)
        try:
            aid = ArtifactId(project_gid=project_gid, entity_type=entity_type)
        except ValueError:
            # A malformed project_gid (the entity_type coerced fine) — a CLIENT input error,
            # NOT a data refusal, and NOT an unservable-entity error (F-1: distinct code, so
            # the diagnostic is not misattributed to the entity_type).
            return self._malformed_identifier(project_gid)
        served = await self._reader.read(aid)
        return serve_result_to_http(served, retry_after_seconds=retry_after_seconds)

    @staticmethod
    def _client_error(code: str, **echoed: str) -> HttpServeResult:
        # Shape-hostile client-error body (no data field). Echoes only the caller's own
        # input token — reveals no other resource (not an enumeration oracle).
        return HttpServeResult(
            status_code=HTTP_STATUS_UNSERVABLE_ENTITY,
            body={"substrate_refused": True, "code": code, **echoed},
            headers={},
            frame=None,
        )

    @classmethod
    def _unservable_entity(cls, entity_type_raw: str) -> HttpServeResult:
        return cls._client_error("SUBSTRATE_UNSERVABLE_ENTITY_TYPE", entity_type=entity_type_raw)

    @classmethod
    def _malformed_identifier(cls, project_gid: str) -> HttpServeResult:
        # F-1: a malformed project_gid gets its OWN code — echoes the gid (caller's own input),
        # never the entity_type (which was valid), so the diagnostic points at the real fault.
        return cls._client_error("SUBSTRATE_MALFORMED_PROJECT_GID", project_gid=project_gid)


# ====================================== CP-6 — persistence-wrapper surface =====


class SubstratePersistenceReader:
    """CP-6: the v2 persistence-wrapper surface — plane-correct BY CONSTRUCTION.

    v1's MISSED layer (``write_section_async`` / ``read_section_async`` /
    ``update_manifest_section_async``) defaulted to the legacy plane when
    ``entity_type`` was omitted — the DEFECT :38 hole the storage-layer call-site
    inventory never saw. The v2 wrapper takes a TYPED ``ArtifactId`` (there is no
    ``entity_type: str | None`` surface to omit) and reads through the choke-point, so
    a plane-blind read is unconstructable, not guarded. Thin: ``read()`` + return the
    ``ServedNumber`` (the caller handles ``Refused`` — the exhaustiveness tooth applies
    at the caller).
    """

    def __init__(self, reader: SubstrateReader) -> None:
        self._reader = reader

    async def read_artifact(self, aid: ArtifactId) -> ServedNumber:
        return await self._reader.read(aid)
