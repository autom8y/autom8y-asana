"""Push GID mappings to autom8_data after index rebuild.

After the cache warmer rebuilds GID indexes, push the mapping snapshot
to autom8_data's sync endpoint so autom8_data can serve GID lookups
locally without calling back to autom8_asana.

The push is best-effort: failure does NOT fail the cache warmer.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from autom8y_config.lambda_extension import resolve_secret_from_env
from autom8y_http import Autom8yHttpClient, HttpClientConfig, TimeoutException
from autom8y_log import get_logger
from pydantic import BaseModel, ConfigDict

from autom8_asana.clients.data._pii import mask_pii_in_string
from autom8_asana.contracts.vocabulary_sync import (
    VocabularyOption,
    VocabularySyncRequest,
    VocabularySyncResponse,
)
from autom8_asana.lambda_handlers.cloudwatch import emit_metric

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.models.custom_field import CustomFieldEnumOption
    from autom8_asana.services.gid_lookup import GidLookupIndex

logger = get_logger(__name__)

# Shared bridge observability namespace (NOT the per-service default
# autom8/lambda). Per SRE observability-design N1 §B-1 / §G-PROPAGATE: the
# StatusPushSkipped skip-reason contract belongs to the shared bridge fleet
# namespace so every bridge workflow inherits it uniformly.
_BRIDGE_FLEET_NAMESPACE = "Autom8y/AsanaBridgeFleet"

# StatusPushSkipped skip_reason dimension values (closed enum).
# Every StatusPush skip path emits StatusPushSkipped{skip_reason=...} so an
# idle skip (benign) and a misconfigured skip (url_absent / invalid_key) are
# distinguishable in CloudWatch. Additive observability only -- emitting this
# counter MUST NOT change push behavior (return values are unchanged).
SKIP_REASON_FEATURE_DISABLED = "feature_disabled"
SKIP_REASON_URL_ABSENT = "url_absent"
SKIP_REASON_INVALID_KEY = "invalid_key"
SKIP_REASON_THREE_WAY_DENOMINATOR_NULL = "three_way_denominator_null"

# StatusPushRowsSkipped skip_class dimension values (closed enum). Per-row
# snapshot guards (sprint-C6): a single defective row must be dropped
# individually with visibility -- NEVER allowed to 422 (invalid phone vs the
# receiver's E.164 OfficePhoneField) or roll back (intra-snapshot duplicate of
# the uq_phone_vertical_pipeline grain) the ENTIRE snapshot INSERT.
SKIP_CLASS_INVALID_PHONE = "invalid_phone"
SKIP_CLASS_DUP_GRAIN = "dup_grain"


def _emit_status_push_skipped(skip_reason: str) -> None:
    """Emit StatusPushSkipped{skip_reason} to the shared bridge namespace.

    Non-blocking: emit_metric() already swallows CloudWatch errors internally
    so observability never fails the push seam.
    """
    emit_metric(
        "StatusPushSkipped",
        1,
        dimensions={"skip_reason": skip_reason},
        namespace=_BRIDGE_FLEET_NAMESPACE,
    )


# Environment variable to disable GID push (emergency kill switch).
# Enabled by default; set to "false", "0", or "no" to disable.
GID_PUSH_ENABLED_ENV_VAR = "GID_PUSH_ENABLED"

# Timeout for the push HTTP request (seconds).
_PUSH_CONFIG = HttpClientConfig(
    connect_timeout=5.0,
    read_timeout=10.0,
    write_timeout=10.0,
    pool_timeout=5.0,
    enable_retry=False,
    enable_circuit_breaker=False,
)


class GidPushResponse(BaseModel):
    """POST /api/v1/gid-mappings/sync response envelope.

    Per ADR-WS1-001: Pydantic BaseModel with extra="ignore".
    Both fields are optional since the upstream response shape
    is not formally documented.
    """

    model_config = ConfigDict(extra="ignore")

    accepted: int | None = None
    replaced: int | None = None


def _is_push_enabled() -> bool:
    """Check whether GID push is enabled via environment variable.

    Returns:
        True unless GID_PUSH_ENABLED is explicitly set to a falsy value.
    """
    val = os.environ.get(GID_PUSH_ENABLED_ENV_VAR, "").lower()
    return val not in {"false", "0", "no"}


def extract_mappings_from_index(
    index: GidLookupIndex,
) -> list[dict[str, str]]:
    """Extract phone/vertical/task_gid mappings from a GidLookupIndex.

    Parses the canonical_key format ``pv1:{phone}:{vertical}`` and pairs
    each entry with its task GID.

    Args:
        index: GidLookupIndex containing the lookup dictionary.

    Returns:
        List of mapping dicts with keys: phone, vertical, task_gid.
        Entries whose canonical_key does not match the expected format
        are silently skipped.
    """
    mappings: list[dict[str, str]] = []
    for canonical_key, task_gid in index._lookup.items():
        parts = canonical_key.split(":")
        # Expected format: pv1:{phone}:{vertical}
        if len(parts) == 3 and parts[0] == "pv1":
            mappings.append(
                {
                    "phone": parts[1],
                    "vertical": parts[2],
                    "task_gid": task_gid,
                }
            )
        else:
            logger.debug(
                "gid_push_skip_entry",
                extra={
                    "canonical_key": canonical_key,
                    "reason": "unexpected_format",
                },
            )
    return mappings


def _get_data_service_url() -> str | None:
    """Resolve the autom8_data base URL from environment.

    Returns:
        Base URL string, or None if not configured.
    """
    return os.environ.get("AUTOM8Y_DATA_URL")


def _get_auth_token() -> str | None:
    """Resolve the S2S JWT token for autom8_data.

    Uses the same ``AUTOM8Y_DATA_API_KEY`` environment variable that
    ``DataServiceClient`` uses, resolved through the Lambda extension
    helper (supports SSM/Secrets Manager ARN references).

    Returns:
        Bearer token string, or None if not available.
    """
    try:
        return resolve_secret_from_env("AUTOM8Y_DATA_API_KEY")
    except ValueError:
        return None


async def _push_to_data_service(
    *,
    endpoint_path: str,
    payload: dict[str, Any],
    response_model: type[BaseModel],
    metric_dimensions: dict[str, str],
    log_prefix: str,
    base_url: str,
    token: str,
    strict_response_parse: bool = False,
    on_response_parse_failure: Callable[[], None] | None = None,
) -> bool:
    """Shared HTTP push helper for data-service endpoints.

    Handles the HTTP POST, response parsing, timeout, and broad-catch
    boilerplate shared by push_gid_mappings_to_data_service,
    push_status_to_data_service, and push_vocabulary_to_data_service.

    2xx-body parse policy (see ``strict_response_parse``): the loose default
    treats a 2xx as success regardless of body parseability (the best-effort
    contract of the ``extra="ignore"`` all-optional siblings, whose upstream
    body shape is not formally documented); strict mode fails CLOSED on a
    2xx body that does not validate against a typed ``extra="forbid"`` contract.

    Args:
        endpoint_path: Path appended to base_url (e.g. '/api/v1/gid-mappings/sync').
        payload: Request body dict to POST as JSON.
        response_model: Pydantic model class to parse the 2xx response body.
        metric_dimensions: Key/value pairs logged with success/failure events.
        log_prefix: Prefix for log event names ('gid_push' or 'status_push').
        base_url: Resolved autom8_data base URL (trailing slash stripped internally).
        token: Bearer token for Authorization header.
        strict_response_parse: 2xx-body parse policy. When False (default, the
            loose best-effort policy for the all-optional ``extra="ignore"``
            siblings), a 2xx whose body fails to validate falls back to argless
            construction and is still reported as success -- the body is
            observability-only. When True (the typed-contract policy), a 2xx
            whose body fails to validate is an UNKNOWN outcome and fails CLOSED
            (returns False) -- NEVER the argless fallback, which for a
            required-field contract would raise, and for a defaulted contract
            would fabricate a false empty-success no-op.
        on_response_parse_failure: Optional hook invoked once when
            strict_response_parse is True AND the 2xx body fails to validate,
            immediately before returning False -- the seam for a domain-specific
            alarm metric. Only fires in strict mode; ignored when
            strict_response_parse is False.

    Returns:
        True if the push succeeded (HTTP 2xx), False otherwise.
    """
    url = f"{base_url.rstrip('/')}{endpoint_path}"
    headers: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    logger.info(
        f"{log_prefix}_starting",
        extra={**metric_dimensions, "url": url},
    )

    try:
        async with (
            Autom8yHttpClient(_PUSH_CONFIG) as client,
            client.raw() as raw_client,
        ):
            response = await raw_client.post(url, json=payload, headers=headers)

        if response.status_code < 300:
            try:
                parsed = response_model.model_validate(response.json())
            except Exception as parse_exc:  # noqa: BLE001
                if strict_response_parse:
                    # STRICT (typed-contract) 2xx-body policy: a 2xx whose body
                    # does not validate against the typed response contract is an
                    # UNKNOWN outcome (did the additive upsert apply? how many
                    # rows inserted/updated/refused? unreadable) -- NOT a benign
                    # success. Fail CLOSED and NEVER fall through to the argless
                    # fallback below, which would fabricate a false empty-success
                    # no-op for a defaulted contract (or raise for a
                    # required-field one). See push_vocabulary_to_data_service.
                    logger.error(
                        f"{log_prefix}_response_parse_failed",
                        extra={
                            **metric_dimensions,
                            "status_code": response.status_code,
                            "error": mask_pii_in_string(str(parse_exc)),
                            "error_type": type(parse_exc).__name__,
                        },
                    )
                    if on_response_parse_failure is not None:
                        on_response_parse_failure()
                    return False
                # LOOSE (best-effort) 2xx-body policy: the upstream body shape is
                # not formally documented, so a 2xx is success regardless of body
                # parseability. Argless construction is the deliberate
                # "body is observability-only" gesture (siblings are all-optional
                # + extra="ignore").
                parsed = response_model()

            logger.info(
                f"{log_prefix}_success",
                extra={
                    **metric_dimensions,
                    "status_code": response.status_code,
                    **{k: v for k, v in parsed.model_dump().items() if v is not None},
                },
            )
            return True

        logger.warning(
            f"{log_prefix}_failed",
            extra={
                **metric_dimensions,
                "status_code": response.status_code,
                "response_text": mask_pii_in_string(response.text[:500]),
            },
        )
        return False

    except TimeoutException as e:
        logger.warning(
            f"{log_prefix}_timeout",
            extra={**metric_dimensions, "error": mask_pii_in_string(str(e))},
        )
        return False

    except (
        Exception  # noqa: BLE001
    ) as e:  # BROAD-CATCH: isolation -- push failure must never fail cache warmer
        logger.error(
            f"{log_prefix}_error",
            extra={
                **metric_dimensions,
                "error": mask_pii_in_string(str(e)),
                "error_type": type(e).__name__,
            },
        )
        return False


async def push_gid_mappings_to_data_service(
    project_gid: str,
    index: GidLookupIndex,
    *,
    data_service_url: str | None = None,
    auth_token: str | None = None,
) -> bool:
    """Push GID mappings to autom8_data after index rebuild.

    Extracts all ``(phone, vertical) -> task_gid`` entries from the
    index and POSTs them to ``POST /api/v1/gid-mappings/sync``.

    This function is **non-blocking** with respect to the caller:
    all exceptions are caught and logged so that a push failure never
    propagates to the cache warmer.

    Args:
        project_gid: Asana project GID that the mappings belong to.
        index: The freshly-built GidLookupIndex to push.
        data_service_url: Override for the autom8_data base URL.
            Defaults to ``AUTOM8Y_DATA_URL`` environment variable.
        auth_token: Override for the S2S JWT bearer token.
            Defaults to ``AUTOM8Y_DATA_API_KEY`` environment variable.

    Returns:
        True if the push succeeded (HTTP 2xx), False otherwise.
    """
    # Feature flag check
    if not _is_push_enabled():
        logger.info(
            "gid_push_disabled",
            extra={
                "project_gid": project_gid,
                "reason": f"{GID_PUSH_ENABLED_ENV_VAR} is false",
            },
        )
        return False

    # Resolve configuration
    base_url = data_service_url or _get_data_service_url()
    if not base_url:
        logger.warning(
            "gid_push_skipped",
            extra={
                "project_gid": project_gid,
                "reason": "AUTOM8Y_DATA_URL not configured",
            },
        )
        return False

    token = auth_token or _get_auth_token()
    if not token:
        logger.warning(
            "gid_push_skipped",
            extra={
                "project_gid": project_gid,
                "reason": "AUTOM8Y_DATA_API_KEY not available",
            },
        )
        return False

    # Extract mappings from index
    mappings = extract_mappings_from_index(index)
    if not mappings:
        logger.info(
            "gid_push_skipped",
            extra={
                "project_gid": project_gid,
                "reason": "no_mappings_to_push",
                "index_size": len(index),
            },
        )
        return True  # Nothing to push is not a failure

    # Build request payload
    payload: dict[str, Any] = {
        "project_gid": project_gid,
        "mappings": mappings,
        "source_timestamp": index.created_at.isoformat(),
        "entry_count": len(mappings),
    }

    return await _push_to_data_service(
        endpoint_path="/api/v1/gid-mappings/sync",
        payload=payload,
        response_model=GidPushResponse,
        metric_dimensions={
            "project_gid": project_gid,
            "entry_count": str(len(mappings)),
        },
        log_prefix="gid_push",
        base_url=base_url,
        token=token,
    )


# ============================================================================
# Account Status Push (ADR-account-status-state-projection)
# ============================================================================

# Pipeline type mapping: Asana project GID -> pipeline_type string
PIPELINE_TYPE_BY_PROJECT_GID: dict[str, str] = {
    "1201081073731555": "unit",  # Business Units
    "1200944186565610": "sales",  # Sales
    "1201319387632570": "onboarding",  # Onboarding
    "1201753128450029": "outreach",  # Outreach
    "1201346565918814": "retention",  # Retention
    "1201265144487549": "reactivation",  # Reactivation
    "1201265144487557": "expansion",  # Expansion
    "1201476141989746": "implementation",  # Implementation
    "1201684018234520": "account_error",  # Account Error
    "1209247943184021": "month1",  # Activation Consultation
}

# Environment variable to disable status push (emergency kill switch).
STATUS_PUSH_ENABLED_ENV_VAR = "STATUS_PUSH_ENABLED"


class AccountStatusPushResponse(BaseModel):
    """POST /api/v1/account-status/sync response envelope."""

    model_config = ConfigDict(extra="ignore")

    deleted: int | None = None
    inserted: int | None = None


def _is_status_push_enabled() -> bool:
    """Check whether status push is enabled via environment variable."""
    val = os.environ.get(STATUS_PUSH_ENABLED_ENV_VAR, "").lower()
    # Enabled by default; set to "false", "0", or "no" to disable
    return val not in {"false", "0", "no"}


def extract_status_from_dataframe(
    df: Any,
    project_gid: str,
    entity_type: str,
) -> list[dict[str, Any]]:
    """Extract account status entries from a warmed DataFrame.

    Classifies each (phone, vertical) row using the appropriate
    SectionClassifier, filtering to only ACTIVE and ACTIVATING
    classifications (active-only registry [SD-02]).

    Args:
        df: Polars DataFrame with columns: office_phone, vertical, gid,
            and section membership data.
        project_gid: Asana project GID for pipeline_type resolution.
        entity_type: Entity type (e.g., 'unit', 'offer').

    Returns:
        List of entry dicts with keys: phone, vertical, pipeline_type,
        account_activity, pipeline_section, stage_entered_at.
    """
    from autom8_asana.models.business.activity import (
        AccountActivity,
        extract_section_name,
        get_classifier,
    )

    pipeline_type = PIPELINE_TYPE_BY_PROJECT_GID.get(project_gid)
    if pipeline_type is None:
        logger.debug(
            "status_extract_unknown_project",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
            },
        )
        return []

    # Get the appropriate classifier
    classifier = get_classifier(entity_type)
    if classifier is None:
        logger.warning(
            "process_pipeline_no_classifier",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )
        return []

    entries: list[dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()

    # Required columns check
    required_cols = {"office_phone"}
    if not required_cols.issubset(set(df.columns)):
        return []

    has_vertical = "vertical" in df.columns
    # Per REVIEW-reconciliation-deep-audit TC-1 / P0-A:
    # Use canonical "section" column from schemas/base.py:84, NOT "section_name"
    has_section = "section" in df.columns
    has_memberships = "memberships" in df.columns

    for row_idx in range(len(df)):
        phone = df["office_phone"][row_idx]
        if not phone:
            continue

        vertical = df["vertical"][row_idx] if has_vertical else ""
        if vertical is None:
            vertical = ""

        # Extract section name from row
        section_name = None
        if has_section:
            section_name = df["section"][row_idx]
        elif has_memberships:
            memberships = df["memberships"][row_idx]
            if memberships is not None:
                section_name = extract_section_name(
                    {"memberships": memberships},
                    project_gid=project_gid,
                )

        if not section_name:
            continue

        # Classify
        activity = classifier.classify(section_name)
        if activity is None:
            continue

        # Active-only registry [SD-02]: only persist ACTIVE and ACTIVATING
        if activity not in (AccountActivity.ACTIVE, AccountActivity.ACTIVATING):
            continue

        entries.append(
            {
                "phone": phone,
                "vertical": str(vertical),
                "pipeline_type": pipeline_type,
                "account_activity": activity.value,
                "pipeline_section": section_name,
                "stage_entered_at": now,  # Overridden by store carry-forward logic
            }
        )

    return entries


def _sanitize_status_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-row guards for the account-status snapshot (sprint-C6, L1 + L3).

    The receiver is a transactional snapshot-replace with ``extra="forbid"``
    entry validation and a ``uq_phone_vertical_pipeline`` UNIQUE constraint, so
    ONE defective row would otherwise reject or roll back the WHOLE snapshot:

    * **L1 -- E.164 per-row skip**: a ``phone`` not matching
      ``E164_PHONE_PATTERN`` (imported from ``autom8y_api_schemas`` -- the SAME
      pattern the receiver's ``OfficePhoneField`` enforces, so drift is
      impossible) drops the ROW, never the snapshot.
    * **L3 -- dup-grain dedupe**: entries sharing a
      ``(phone, vertical, pipeline_type)`` grain (mirrors
      ``uq_phone_vertical_pipeline``) keep the FIRST occurrence (deterministic
      given the stable entity/row iteration order) and drop later ones -- an
      intra-snapshot duplicate would roll back the entire receiver INSERT.

    Anything dropped is surfaced via ``status_push_rows_skipped`` (WARNING) +
    ``StatusPushRowsSkipped{skip_class}`` counters. Never raises; pure
    function of ``entries``.

    Args:
        entries: Candidate status entry dicts.

    Returns:
        The sanitized entry list (possibly empty).
    """
    import re

    from autom8y_api_schemas.fields import E164_PHONE_PATTERN

    phone_pattern = re.compile(E164_PHONE_PATTERN)

    sanitized: list[dict[str, Any]] = []
    seen_grains: set[tuple[Any, Any, Any]] = set()
    invalid_phone_count = 0
    dup_grain_count = 0
    first_bad_phone: str | None = None

    for entry in entries:
        phone = entry.get("phone")
        if not isinstance(phone, str) or not phone_pattern.match(phone):
            invalid_phone_count += 1
            if first_bad_phone is None:
                first_bad_phone = str(phone)
            continue

        grain = (phone, entry.get("vertical"), entry.get("pipeline_type"))
        if grain in seen_grains:
            dup_grain_count += 1
            continue
        seen_grains.add(grain)
        sanitized.append(entry)

    if invalid_phone_count or dup_grain_count:
        logger.warning(
            "status_push_rows_skipped",
            extra={
                "invalid_phone_count": invalid_phone_count,
                "dup_grain_count": dup_grain_count,
                "kept_count": len(sanitized),
                "sample": (
                    mask_pii_in_string(first_bad_phone) if first_bad_phone is not None else None
                ),
            },
        )
        if invalid_phone_count:
            emit_metric(
                "StatusPushRowsSkipped",
                invalid_phone_count,
                dimensions={"skip_class": SKIP_CLASS_INVALID_PHONE},
                namespace=_BRIDGE_FLEET_NAMESPACE,
            )
        if dup_grain_count:
            emit_metric(
                "StatusPushRowsSkipped",
                dup_grain_count,
                dimensions={"skip_class": SKIP_CLASS_DUP_GRAIN},
                namespace=_BRIDGE_FLEET_NAMESPACE,
            )

    return sanitized


async def push_status_to_data_service(
    entries: list[dict[str, Any]],
    source_timestamp: str,
    *,
    data_service_url: str | None = None,
    auth_token: str | None = None,
) -> bool:
    """Push account status snapshot to autom8_data.

    Mirrors push_gid_mappings_to_data_service() pattern.
    Non-blocking: all exceptions are caught and logged so that
    a push failure never propagates to the cache warmer.

    Args:
        entries: List of status entry dicts.
        source_timestamp: ISO timestamp of snapshot generation.
        data_service_url: Override for the autom8_data base URL.
        auth_token: Override for the S2S JWT bearer token.

    Returns:
        True if the push succeeded (HTTP 2xx), False otherwise.
    """
    if not _is_status_push_enabled():
        logger.info(
            "status_push_disabled",
            extra={"reason": f"{STATUS_PUSH_ENABLED_ENV_VAR} is false"},
        )
        _emit_status_push_skipped(SKIP_REASON_FEATURE_DISABLED)
        return False

    base_url = data_service_url or _get_data_service_url()
    if not base_url:
        logger.warning(
            "status_push_skipped",
            extra={"reason": "AUTOM8Y_DATA_URL not configured"},
        )
        _emit_status_push_skipped(SKIP_REASON_URL_ABSENT)
        return False

    token = auth_token or _get_auth_token()
    if not token:
        logger.warning(
            "status_push_skipped",
            extra={"reason": "AUTOM8Y_DATA_API_KEY not available"},
        )
        _emit_status_push_skipped(SKIP_REASON_INVALID_KEY)
        return False

    # Per-row guards (sprint-C6): drop E.164-invalid phones + intra-snapshot
    # duplicate grains BEFORE the empty-entries check, so a defective row can
    # never fail the whole snapshot. If sanitization empties the list, the
    # no_entries_to_push skip below still applies -- but the
    # status_push_rows_skipped warning has already made it non-silent.
    entries = _sanitize_status_entries(entries)

    if not entries:
        logger.info(
            "status_push_skipped",
            extra={"reason": "no_entries_to_push"},
        )
        return True  # Nothing to push is not a failure

    payload: dict[str, Any] = {
        "source": "section_classifier",
        "entries": entries,
        "source_timestamp": source_timestamp,
        "entry_count": len(entries),
    }

    return await _push_to_data_service(
        endpoint_path="/api/v1/account-status/sync",
        payload=payload,
        response_model=AccountStatusPushResponse,
        metric_dimensions={"entry_count": str(len(entries))},
        log_prefix="status_push",
        base_url=base_url,
        token=token,
    )


# ============================================================================
# Vocabulary Sync Push (ADR-dyn-enum-contract-shared-contract)
# ============================================================================
#
# Carries an Asana Vertical enum-option-SET change into autom8y-data via ONE
# typed, additive, FK-safe contract (contracts/vocabulary_sync.py). Sprint-1 is
# the PRODUCER half: read -> project (NAME-key) -> refuse-or-push. It is
# SHIP-DARK -- gated behind a NEW flag defaulting OFF (VOCAB_SYNC_ENABLED). The
# consumer endpoint + additive-upsert store are sprint-2 (autom8y-data).
#
# Two-sided producer REFUSE (defense-in-depth on what the producer can SEE):
#   * EMPTY read            -> REFUSE + ALERT, publish nothing.
#   * GROSS-TRUNCATION      -> REFUSE + ALERT, publish nothing (len < floor).
#   * HEALTHY full set      -> project + (would-)publish.
# The DEEP 3-edge FK-referential-coverage refuse is the CONSUMER's (sprint-2):
# the FK-child tables (campaigns / asset_verticals / offers.category) live in
# autom8y-data, so the producer CANNOT compute the "missing-referenced-key"
# check. Its guard is a cheap backstop against a catastrophic degraded read
# from the Asana API before transport -- correct layering, not a bandaid.

# Environment variable to ENABLE vocabulary sync. SHIP-DARK: DEFAULT OFF.
# Enabled ONLY when explicitly truthy -- deliberately NOT the default-ON idiom
# of GID_PUSH_ENABLED / STATUS_PUSH_ENABLED (reusing either would ship the vocab
# path live-by-default, the opposite of ship-dark).
VOCAB_SYNC_ENABLED_ENV_VAR = "VOCAB_SYNC_ENABLED"

# Operator-tunable GROSS-TRUNCATION floor. Default 1 -> only a truly-empty set
# trips 'empty'; a legitimately-small set never false-positives. Operators
# SHOULD raise this near the known population at enable time. The consumer's
# "~40 verticals" hint is CONSUMER knowledge -- NOT hardcoded producer-side; the
# lever is exposed instead.
VOCAB_SYNC_MIN_OPTIONS_ENV_VAR = "VOCAB_SYNC_MIN_OPTIONS"
_VOCAB_SYNC_MIN_OPTIONS_DEFAULT = 1

# VocabSyncRefused refuse_reason dimension values (closed enum). A REFUSE is the
# ALARMING signal -- a deploy-gate alarm keys on VocabSyncRefused (NFR-004).
VOCAB_REFUSE_REASON_EMPTY = "empty"
VOCAB_REFUSE_REASON_GROSS_TRUNCATION = "gross_truncation"

# VocabSyncDriftDetected drift_reason dimension values (closed enum). Drift is a
# WARNING signal, NOT a refuse: the sync PROCEEDS -- disabled/collided options
# RIDE the envelope (present-but-flagged); the observer NEVER codegens, mints, or
# deletes (ADR-S4-001 / FR-006, the WARN-first registry.py "read-only comparator"
# discipline). ONE metric, drift_reason-discriminated -- the principled
# composition with the VocabSyncRefused{refuse_reason} family above, NOT a
# proliferation of metric names.
VOCAB_DRIFT_REASON_NAME_COLLISION = "name_collision"
VOCAB_DRIFT_REASON_DISABLED_OPTION = "disabled_option"
VOCAB_DRIFT_REASON_DEGENERATE_NAME = "degenerate_name"


def _is_vocab_sync_enabled() -> bool:
    """Check whether vocabulary sync is enabled (SHIP-DARK: DEFAULT OFF).

    Mirrors the DEFAULT-OFF idiom of ASANA_VERTICAL_BACKFILL_ENABLED
    (cache_warmer.py:242), NOT the default-ON _is_push_enabled (gid_push.py:95).

    Returns:
        True ONLY when VOCAB_SYNC_ENABLED is explicitly truthy. Unset -> False.
    """
    return os.environ.get(VOCAB_SYNC_ENABLED_ENV_VAR, "").lower() in ("1", "true", "yes")


def _get_vocab_sync_min_options() -> int:
    """Resolve the operator-tunable GROSS-TRUNCATION floor.

    Returns:
        The env-configured integer floor, or _VOCAB_SYNC_MIN_OPTIONS_DEFAULT (1)
        when unset or non-parseable. Values < 1 are clamped to the default so
        the guard can never be disabled into a no-op.
    """
    raw = os.environ.get(VOCAB_SYNC_MIN_OPTIONS_ENV_VAR, "")
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return _VOCAB_SYNC_MIN_OPTIONS_DEFAULT
    return val if val >= 1 else _VOCAB_SYNC_MIN_OPTIONS_DEFAULT


def _emit_vocab_sync_refused(refuse_reason: str, option_count: int) -> None:
    """Emit VocabSyncRefused{refuse_reason,option_count} to the bridge namespace.

    The distinct metric name enables a deploy-gate alarm (NFR-004). Non-blocking:
    emit_metric() swallows CloudWatch errors internally so observability never
    fails the push seam.
    """
    emit_metric(
        "VocabSyncRefused",
        1,
        dimensions={"refuse_reason": refuse_reason, "option_count": str(option_count)},
        namespace=_BRIDGE_FLEET_NAMESPACE,
    )


def _emit_vocab_sync_skipped(skip_reason: str) -> None:
    """Emit VocabSyncSkipped{skip_reason} to the shared bridge namespace.

    Benign/config skip observability (feature_disabled / url_absent /
    invalid_key), distinct from the ALARMING VocabSyncRefused. Reuses the
    shared SKIP_REASON_* closed enum. Non-blocking.
    """
    emit_metric(
        "VocabSyncSkipped",
        1,
        dimensions={"skip_reason": skip_reason},
        namespace=_BRIDGE_FLEET_NAMESPACE,
    )


def _emit_vocab_sync_contract_parse_failed(field_key: str) -> None:
    """Emit VocabSyncContractParseFailed{field_key} to the shared bridge namespace.

    A 2xx whose body does NOT validate against the typed VocabularySyncResponse
    contract is an UNKNOWN-outcome failure: the additive accounting
    (inserted/updated/refused) is unreadable, so the producer cannot know whether
    -- or how partially -- the sync applied. This is a DISTINCT, ALARMING failure
    class from a producer-side REFUSE (pre-transport, on empty/gross-truncation)
    and from a benign config SKIP; a deploy-gate alarm SHOULD key on it alongside
    VocabSyncRefused (NFR-004). Non-blocking: emit_metric() swallows CloudWatch
    errors internally so observability never fails the push seam.
    """
    emit_metric(
        "VocabSyncContractParseFailed",
        1,
        dimensions={"field_key": field_key},
        namespace=_BRIDGE_FLEET_NAMESPACE,
    )


def _emit_vocab_sync_drift(drift_reason: str, count: int, field_key: str) -> None:
    """Emit VocabSyncDriftDetected{drift_reason,count,field_key} + a WARNING log.

    The producer-side vocab-health WARN. Drift is a *signal*, NOT a refuse: the
    sync PROCEEDS and the drifting options RIDE the envelope. This mirror of
    _emit_vocab_sync_refused (one metric, reason-discriminated) is the exact
    WARN-first discipline of the origin/main registry.py drift gate
    (``logger.warning("model_schema_drift_detected", … "ModelSchemaDrift" …)`` --
    "HONORS ADR-S4-001: read-only comparator"): it observes what already flows and
    alarms; it NEVER writes a schema, mints a vertical, or deletes an option.

    The log is WARNING (not ERROR) precisely because drift != refuse -- a
    deploy-gate alarm keys on VocabSyncDriftDetected at a distinct (lower) tier
    from the ALARMING VocabSyncRefused. Non-blocking: emit_metric() swallows
    CloudWatch errors internally so observability never fails the push seam.
    """
    emit_metric(
        "VocabSyncDriftDetected",
        1,
        dimensions={
            "drift_reason": drift_reason,
            "count": str(count),
            "field_key": field_key,
        },
        namespace=_BRIDGE_FLEET_NAMESPACE,
    )
    logger.warning(
        "vocab_sync_drift_detected",
        extra={"drift_reason": drift_reason, "count": count, "field_key": field_key},
    )


def normalize_vertical_key(name: str) -> str:
    """Deterministic NAME-key normalization (Lock-3: normalize(option.name)).

    Collapses the two cross-service-unsafe axes -- surrounding/internal
    whitespace and letter case -- so display-name variants round-trip to ONE
    stable key (e.g. ``"General Practice"`` and ``" general  practice "`` both
    -> ``"general practice"``). Pure and side-effect-free.

    The exact canonical form is validated against the consumer's existing
    ``verticals.key`` set by the sprint-4 read-only dry-run (RR3); sprint-1 owns
    a deterministic, testable normalization only -- NOT the first-sync MATCH.

    Args:
        name: The Asana enum option display name.

    Returns:
        The normalized cross-service key. NEVER the ``enum_option.gid`` nor the
        consumer ``vertical_id`` (Lock-3).
    """
    return " ".join(name.split()).lower()


def project_enum_options_to_vocabulary_options(
    enum_options: list[CustomFieldEnumOption] | None,
) -> list[VocabularyOption]:
    """Project the live Asana option-SET onto the typed wire contract.

    This is the option-SET read (the full set of choices), distinct from the
    per-entry *selected* value that is the untyped gap today (gid_push.py:490 /
    default.py:258-263). Each option becomes a VocabularyOption keyed on the
    Lock-3 NAME-key; ``enabled`` rides along for drift-observability only.

    An option whose name is None -- or blank / whitespace-only, which
    ``normalize_vertical_key`` would collapse to the degenerate empty key ``""``
    -- cannot yield a usable NAME-key (Lock-3), so it is skipped; the downstream
    emptiness/floor guard still sees the reduced usable count, which correctly
    treats a read that lost its names as degraded. No ``VocabularyOption`` with
    an empty ``vertical_key`` ever reaches the wire.

    Args:
        enum_options: ``CustomField.enum_options`` from a live/mocked read, or
            None when the read returned nothing.

    Returns:
        The projected option-SET (may be empty -- the caller's guard decides).
    """
    if not enum_options:
        return []
    projected: list[VocabularyOption] = []
    for opt in enum_options:
        if opt.name is None or not opt.name.strip():
            continue
        projected.append(
            VocabularyOption(
                vertical_key=normalize_vertical_key(opt.name),
                name=opt.name,
                enabled=opt.enabled,
            )
        )
    return projected


def detect_vocab_drift(
    projected: list[VocabularyOption],
    *,
    raw_option_count: int | None = None,
) -> list[tuple[str, int]]:
    """Read-only drift signals over the option-SET that WILL ship. Pure.

    A read-only comparator in the exact discipline of the origin/main registry.py
    WARN-first drift gate ("HONORS ADR-S4-001: read-only comparator. It never
    writes a schema, generates a column, or mutates a descriptor"): this observer
    NEVER mutates/mints/deletes -- it inspects the projected set and returns the
    drift classes PRESENT. The caller emits one WARN+metric per signal, then
    pushes UNCHANGED. Drift is a signal, not a refuse.

    Three producer-observable classes (none removes a valid option; none is a
    delete -- disabled/collided options RIDE the envelope present-but-flagged;
    degenerate options never had a constructible NAME-key to begin with and were
    already skipped by projection at the ``opt.name`` guard):

    * **name_collision** -- 2+ options normalized to the SAME ``vertical_key``
      (``len(projected) - len(distinct keys)``). Both rows still ride; the
      consumer's FR-007 per-row guard resolves the collision at upsert time.
    * **disabled_option** -- an option carried with ``enabled is False``. It rides
      the envelope with ``enabled=False`` (drift-observability only; ``enabled`` is
      not a stored column). A disabled-but-referenced option is a WARN, never a
      DELETE (RR2 / BC-3).
    * **degenerate_name** (only when ``raw_option_count`` is threaded) -- raw
      options that lost their NAME-key (None / blank) and were dropped by
      projection (``raw_option_count - len(projected)``). The cheap producer-side
      read-*quality* proxy; true prior-set churn (a DROP vs a prior known set) is
      NOT producer-observable ship-dark (stateless single read, CON-008) and is
      the consumer's response-accounting signal, deferred.

    Args:
        projected: The projected VocabularyOption SET that will ship (post-floor).
        raw_option_count: The pre-projection raw option count, threaded by the
            caller to enable the degenerate_name signal. When None, that signal is
            simply not computed (no false positives).

    Returns:
        ``[(drift_reason, count), …]`` for each class PRESENT; an empty list for a
        clean set. Order is stable: collision, disabled, degenerate.
    """
    signals: list[tuple[str, int]] = []

    # (a) NAME-COLLISION -- 2+ options normalized to the SAME vertical_key.
    collision_count = len(projected) - len({o.vertical_key for o in projected})
    if collision_count > 0:
        signals.append((VOCAB_DRIFT_REASON_NAME_COLLISION, collision_count))

    # (b) DISABLED-CARRIED -- an option riding the envelope with enabled=False.
    disabled_count = sum(1 for o in projected if o.enabled is False)
    if disabled_count > 0:
        signals.append((VOCAB_DRIFT_REASON_DISABLED_OPTION, disabled_count))

    # (c) DEGENERATE-DROP -- raw options that lost their NAME-key (None/blank) and
    #     were skipped by projection. Only computed when the caller threads the
    #     raw count (the projected set alone cannot see what projection dropped).
    if raw_option_count is not None:
        degenerate_count = raw_option_count - len(projected)
        if degenerate_count > 0:
            signals.append((VOCAB_DRIFT_REASON_DEGENERATE_NAME, degenerate_count))

    return signals


async def push_vocabulary_to_data_service(
    options: list[VocabularyOption] | None,
    *,
    field_key: Literal["vertical"] = "vertical",
    raw_option_count: int | None = None,
    data_service_url: str | None = None,
    auth_token: str | None = None,
) -> bool:
    """Push the Asana Vertical enum option-SET to autom8_data (SHIP-DARK).

    Gated behind VOCAB_SYNC_ENABLED (DEFAULT OFF): unset -> nothing crosses the
    seam. Reuses the endpoint-parameterized _push_to_data_service helper with the
    Lock-1 generic plural path ``/api/v1/vocabularies/sync`` (NEVER
    ``/verticals/sync``). Non-blocking with respect to the caller: all
    exceptions are caught and logged inside the shared helper so a push failure
    never propagates to the cache warmer (mirrors push_status_to_data_service).

    The producer REFUSE-layer fires BEFORE any transport or credential
    resolution, so a broken read is refused with the correct signal regardless
    of transport config:

      * EMPTY (options None / len == 0)      -> refuse_reason="empty"
      * GROSS-TRUNCATION (0 < len < floor)   -> refuse_reason="gross_truncation"

    Args:
        options: The projected VocabularyOption SET (see
            project_enum_options_to_vocabulary_options), or None for an empty read.
        field_key: The Lock-2 discriminator (only ``"vertical"`` this instance).
        raw_option_count: The pre-projection raw option count, threaded to enable
            the degenerate_name drift signal (raw options that lost their NAME-key
            and were dropped by projection). Optional -- when None, degenerate_name
            is not computed. Observability only; does not affect what ships.
        data_service_url: Override for the autom8_data base URL.
        auth_token: Override for the S2S JWT bearer token.

    Returns:
        True if the push succeeded (HTTP 2xx). False on ship-dark skip, any
        REFUSE, missing config, or push failure.
    """
    # 1. Ship-dark flag gate (DEFAULT OFF) -- first line, before anything else.
    if not _is_vocab_sync_enabled():
        logger.info(
            "vocab_sync_disabled",
            extra={"reason": f"{VOCAB_SYNC_ENABLED_ENV_VAR} is not enabled (ship-dark)"},
        )
        _emit_vocab_sync_skipped(SKIP_REASON_FEATURE_DISABLED)
        return False

    # 2. Producer refuse-layer -- BEFORE any transport. Refuses on what the
    #    producer can SEE (empty / gross-truncation vs floor). The DEEP 3-edge
    #    FK-coverage refuse is the consumer's (sprint-2).
    opts = options or []
    option_count = len(opts)
    if option_count == 0:
        logger.error(
            "vocab_sync_refused",
            extra={"refuse_reason": VOCAB_REFUSE_REASON_EMPTY, "option_count": 0},
        )
        _emit_vocab_sync_refused(VOCAB_REFUSE_REASON_EMPTY, 0)
        return False

    floor = _get_vocab_sync_min_options()
    if option_count < floor:
        logger.error(
            "vocab_sync_refused",
            extra={
                "refuse_reason": VOCAB_REFUSE_REASON_GROSS_TRUNCATION,
                "option_count": option_count,
                "floor": floor,
            },
        )
        _emit_vocab_sync_refused(VOCAB_REFUSE_REASON_GROSS_TRUNCATION, option_count)
        return False

    # 2b. DRIFT-WARN observability -- AFTER the floor passes (observe what SHIPS),
    #     BEFORE transport. Read-only: one WARN+metric per drift class, then the
    #     push PROCEEDS UNCHANGED. Drift is a signal, not a refuse -- disabled and
    #     collided options RIDE the envelope (present-but-flagged); NEVER
    #     codegen/mint/delete (ADR-S4-001 / FR-006). On the REFUSED path above the
    #     louder VocabSyncRefused already fired; drift is emitted only over the set
    #     that WILL ship. The observer is pure + the emitter non-fatal, so this is
    #     strictly-additive to the shipping path.
    for drift_reason, drift_count in detect_vocab_drift(opts, raw_option_count=raw_option_count):
        _emit_vocab_sync_drift(drift_reason, drift_count, field_key)

    # 3. Resolve transport config (mirrors push_status_to_data_service).
    base_url = data_service_url or _get_data_service_url()
    if not base_url:
        logger.warning(
            "vocab_sync_skipped",
            extra={"reason": "AUTOM8Y_DATA_URL not configured"},
        )
        _emit_vocab_sync_skipped(SKIP_REASON_URL_ABSENT)
        return False

    token = auth_token or _get_auth_token()
    if not token:
        logger.warning(
            "vocab_sync_skipped",
            extra={"reason": "AUTOM8Y_DATA_API_KEY not available"},
        )
        _emit_vocab_sync_skipped(SKIP_REASON_INVALID_KEY)
        return False

    # 4. Build the typed request + push via the Lock-1 generic path.
    #    STRICT 2xx-body policy: VocabularySyncResponse is a required-field,
    #    extra="forbid" contract, so a 2xx whose body does not validate is an
    #    UNKNOWN outcome -- fail CLOSED (never the argless fallback the
    #    extra="ignore" siblings rely on) and raise the VocabSyncContractParseFailed
    #    alarm. This path's fail-closed correctness must NOT depend on whether
    #    VocabularySyncResponse happens to be argless-constructible.
    request = VocabularySyncRequest(field_key=field_key, options=opts)
    return await _push_to_data_service(
        endpoint_path="/api/v1/vocabularies/sync",
        payload=request.model_dump(mode="json"),
        response_model=VocabularySyncResponse,
        metric_dimensions={"field_key": field_key, "option_count": str(option_count)},
        log_prefix="vocab_sync",
        base_url=base_url,
        token=token,
        strict_response_parse=True,
        on_response_parse_failure=lambda: _emit_vocab_sync_contract_parse_failed(field_key),
    )
