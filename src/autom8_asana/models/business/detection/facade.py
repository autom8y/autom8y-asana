"""Detection facade - main orchestration functions.

Per PRD-CACHE-PERF-DETECTION: Caches Tier 4 detection results for performance.

This module provides the main detection entry points that coordinate the tier chain:
- detect_entity_type(): Sync detection (Tiers 1-3, no API)
- detect_entity_type_async(): Async detection (Tiers 1-5, optional API)
- identify_holder_type(): Holder identification with fallback

The facade orchestrates tiers but contains no tier-specific logic.

Dependencies: types.py, config.py, tier1.py, tier2.py, tier3.py, tier4.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger
from pydantic import ValidationError

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.core.errors import CACHE_TRANSIENT_ERRORS
from autom8_asana.core.types import EntityType
from autom8_asana.models.business.detection.config import (
    get_holder_attr,
)
from autom8_asana.models.business.detection.tier1 import (
    _detect_tier1_project_membership_async,
    detect_by_project_membership,
)
from autom8_asana.models.business.detection.tier2 import (
    _detect_by_name_pattern,
)
from autom8_asana.models.business.detection.tier3 import (
    detect_by_parent_inference,
)
from autom8_asana.models.business.detection.tier4 import (
    detect_by_structure_inspection,
)
from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_5,
    DetectionResult,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

__all__ = [
    "detect_by_project",
    "detect_by_parent",
    "detect_by_structure_async",
    "detect_entity_type",
    "detect_entity_type_async",
    "detect_entity_type_from_dict",
    "identify_holder_type",
    "_matches_holder_pattern",
]

from autom8_asana.settings import get_settings

logger = get_logger(__name__)

# Per PRD-CACHE-PERF-DETECTION FR-VERSION-003: TTL matches task cache (300s)
# Configurable via ASANA_CACHE_TTL_DETECTION environment variable
DETECTION_CACHE_TTL = get_settings().cache.ttl_detection


# --- Detection Cache Helpers ---
# Per TDD-CACHE-PERF-DETECTION: Inline cache logic around Tier 4


def _get_cached_detection(
    task_gid: str,
    cache: object,
) -> DetectionResult | None:
    """Retrieve cached detection result for task GID.

    Per FR-CACHE-001: Check cache before Tier 4 execution.
    Per FR-DEGRADE-001: Returns None on any cache error.

    Args:
        task_gid: The task GID to look up.
        cache: Cache provider instance (duck-typed for get method).

    Returns:
        DetectionResult if cache hit and valid, None otherwise.
    """
    try:
        entry = cache.get(task_gid, EntryType.DETECTION)  # type: ignore[attr-defined]
        if entry is None:
            return None

        # Check TTL expiration
        if entry.is_expired():
            return None

        # Deserialize DetectionResult from cached dict
        data = entry.data
        return DetectionResult(
            entity_type=EntityType(data["entity_type"]),
            confidence=data["confidence"],
            tier_used=data["tier_used"],
            needs_healing=data["needs_healing"],
            expected_project_gid=data["expected_project_gid"],
        )
    except (
        CACHE_TRANSIENT_ERRORS
    ):  # metrics -- per FR-DEGRADE-001, cache lookup failures don't prevent detection
        logger.debug("Detection cache lookup failed", exc_info=True)
        return None


def _cache_detection_result(
    task: Task,
    result: DetectionResult,
    cache: object,
) -> None:
    """Cache a detection result for future lookups.

    Per FR-CACHE-002: Store result after Tier 4 success.
    Per FR-CACHE-005: Only cache non-None Tier 4 results.
    Per FR-CACHE-006: Do not cache UNKNOWN (Tier 5).
    Per FR-DEGRADE-002: Cache storage failures don't prevent detection.

    Args:
        task: The task that was detected.
        result: The DetectionResult to cache.
        cache: Cache provider instance (duck-typed for set method).
    """
    # FR-CACHE-006: Don't cache UNKNOWN results
    if result.entity_type == EntityType.UNKNOWN:
        return

    # Serialize DetectionResult to dict
    # Per FR-ENTRY-003: All 5 fields preserved with EntityType as string
    data = {
        "entity_type": result.entity_type.value,
        "confidence": result.confidence,
        "tier_used": result.tier_used,
        "needs_healing": result.needs_healing,
        "expected_project_gid": result.expected_project_gid,
    }

    # Per FR-VERSION-001: Use task.modified_at as version when available
    # Per FR-VERSION-002: Fall back to current time if modified_at is None
    if task.modified_at:
        # Parse ISO 8601 string to datetime
        modified_str = task.modified_at
        if modified_str.endswith("Z"):
            modified_str = modified_str[:-1] + "+00:00"
        version = datetime.fromisoformat(modified_str)
        if version.tzinfo is None:
            version = version.replace(tzinfo=UTC)
    else:
        version = datetime.now(UTC)

    entry = CacheEntry(
        key=task.gid,
        data=data,
        entry_type=EntryType.DETECTION,
        version=version,
        ttl=DETECTION_CACHE_TTL,
    )

    try:
        cache.set(task.gid, entry)  # type: ignore[attr-defined]
    except (
        CACHE_TRANSIENT_ERRORS
    ):  # metrics -- per FR-DEGRADE-002, cache storage failures don't prevent detection
        logger.warning(
            "detection_cache_store_failed_silent",
            extra={
                "task_gid": task.gid,
                "entry_type": EntryType.DETECTION.value,
            },
            exc_info=True,
        )


# --- Utility Functions ---


def detect_entity_type_from_dict(data: dict[str, Any]) -> str | None:
    """Detect entity type from raw task data dict.

    Convenience wrapper for TTL resolution and cache builders that work with
    raw dicts before Task model instantiation. Uses lazy imports to avoid
    circular dependencies at module load time.

    Args:
        data: Raw task data dict (as returned by Asana API).

    Returns:
        Entity type value string (e.g., "business", "contact") or None
        if detection fails or model validation fails.

    Example:
        >>> entity_type = detect_entity_type_from_dict({"gid": "123", "name": "Contacts"})
        >>> if entity_type:
        ...     ttl = DEFAULT_ENTITY_TTLS.get(entity_type.lower(), DEFAULT_TTL)
    """
    try:
        from autom8_asana.models import Task as TaskModel

        temp_task = TaskModel.model_validate(data)
        result = detect_entity_type(temp_task)
        if result and result.entity_type:
            return result.entity_type.value
        return None
    except ImportError:
        return None
    except (
        ValidationError,
        KeyError,
        AttributeError,
    ):  # vendor-polymorphic -- model_validate can raise diverse pydantic errors
        logger.debug("Detection result fetch failed", exc_info=True)
        return None


def detect_by_project(task: Task) -> DetectionResult | None:
    """Tier 1: Detect entity type by project membership.

    Per TDD-DETECTION/FR-DET-002: O(1) registry lookup, no API call.

    This is the primary detection method. It looks up the task's first project
    membership in the ProjectTypeRegistry for deterministic type detection.

    Args:
        task: Task to detect type for.

    Returns:
        DetectionResult if project GID is registered, None otherwise.

    Example:
        >>> result = detect_by_project(task)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name} via project membership")
    """
    return detect_by_project_membership(task)


def detect_by_parent(task: Task, parent_type: EntityType) -> DetectionResult | None:
    """Tier 3: Detect entity type by parent type inference.

    Per TDD-DETECTION: Infer child type from known parent type.

    This is used when we know the parent's type and can infer the child's type.
    For example, children of a CONTACT_HOLDER are CONTACT entities.

    Args:
        task: Task to detect type for (used for expected_project_gid lookup).
        parent_type: Known parent EntityType.

    Returns:
        DetectionResult if parent type has a known child mapping, None otherwise.

    Example:
        >>> result = detect_by_parent(task, EntityType.CONTACT_HOLDER)
        >>> result.entity_type  # EntityType.CONTACT
    """
    return detect_by_parent_inference(task, parent_type)


async def detect_by_structure_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Tier 4: Detect entity type by subtask structure inspection.

    Per TDD-DETECTION/ADR-0094: Async detection via API call.

    This is the fallback when sync detection tiers fail. It fetches subtasks
    and examines their names to infer the parent entity type.

    - Business has holder subtasks: "contacts", "units", "location"
    - Unit has holder subtasks: "offers", "processes"

    Args:
        task: Task to detect type for.
        client: AsanaClient for API calls.

    Returns:
        DetectionResult if structure matches a known pattern, None otherwise.
    """
    return await detect_by_structure_inspection(task, client)


# --- Tier 5: Unknown Fallback ---


def _make_unknown_result(task: Task) -> DetectionResult:
    """Create Tier 5 UNKNOWN result.

    Per TDD-DETECTION: Fallback when all detection tiers fail.

    Args:
        task: Task that could not be detected (for logging).

    Returns:
        DetectionResult with UNKNOWN type and needs_healing=True.
    """
    # Log with diagnostic info to help identify why detection failed
    first_project_gid = None
    if task.memberships:
        first_membership = task.memberships[0]
        project_data = (
            first_membership.get("project") if isinstance(first_membership, dict) else None
        )
        first_project_gid = project_data.get("gid") if project_data else None

    logger.warning(
        "tier5_fallback",
        extra={
            "task_gid": task.gid,
            "task_name": task.name,
            "has_memberships": bool(task.memberships),
            "memberships_count": len(task.memberships) if task.memberships else 0,
            "first_project_gid": first_project_gid,
        },
    )

    return DetectionResult(
        entity_type=EntityType.UNKNOWN,
        confidence=CONFIDENCE_TIER_5,
        tier_used=5,
        needs_healing=True,
        expected_project_gid=None,
    )


# --- Unified Detection Functions ---


def detect_entity_type(
    task: Task,
    parent_type: EntityType | None = None,
) -> DetectionResult:
    """Synchronous entity type detection (Tiers 1-3).

    Per TDD-DETECTION/FR-DET-007: Synchronous function for zero-API-call detection.

    Executes tiers in order, returning on first success:
    1. Project membership lookup (O(1), no API)
    2. Name pattern matching (string ops, no API)
    3. Parent type inference (logic only, no API)

    If all tiers fail, returns UNKNOWN with needs_healing=True.

    Args:
        task: Task to detect type for.
        parent_type: Known parent type for Tier 3 inference.

    Returns:
        DetectionResult with detected type and metadata.

    Example:
        >>> result = detect_entity_type(task)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name}")
        >>> if result.is_deterministic:
        ...     print("Detected via project membership (Tier 1)")
    """
    # Tier 1: Project membership
    result = detect_by_project_membership(task)
    if result:
        return result

    # Tier 2: Name patterns
    result = _detect_by_name_pattern(task)
    if result:
        return result

    # Tier 3: Parent inference
    if parent_type:
        result = detect_by_parent_inference(task, parent_type)
        if result:
            return result

    # Tier 5: Unknown (skip Tier 4 in sync path)
    return _make_unknown_result(task)


async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Asynchronous entity type detection (Tiers 1-5).

    Per TDD-DETECTION/FR-DET-008: Async function with optional Tier 4.
    Per TDD-WORKSPACE-PROJECT-REGISTRY: Async Tier 1 with lazy discovery FIRST.
    Per ADR-0109: Discovery triggered on first unregistered GID.
    Per PRD-CACHE-PERF-DETECTION: Cache integration around Tier 4.

    Detection order:
    1. Async Tier 1: Project membership with lazy workspace discovery
    2-3. Sync tiers: Name patterns, parent inference (no API)
    4. [CACHE CHECK] - only when allow_structure_inspection=True
    4. Structure inspection (requires API call, disabled by default)
    5. UNKNOWN fallback

    Cache Behavior (per PRD-CACHE-PERF-DETECTION):
    - Cache check occurs ONLY before Tier 4, not at function entry
    - Successful Tier 4 results are cached with task.modified_at version
    - UNKNOWN results are NOT cached (should retry on next call)
    - Cache failures degrade gracefully (detection proceeds normally)

    Args:
        task: Task to detect type for.
        client: AsanaClient for Tier 1 discovery and Tier 4 API calls.
        parent_type: Known parent type for Tier 3 inference.
        allow_structure_inspection: Enable Tier 4 (default: False).

    Returns:
        DetectionResult with detected type and metadata.

    Example:
        >>> # Fast path: async Tier 1 with discovery, then sync tiers
        >>> result = await detect_entity_type_async(task, client)

        >>> # Full detection with structure inspection (uses cache)
        >>> result = await detect_entity_type_async(
        ...     task, client, allow_structure_inspection=True
        ... )
    """
    # NEW: Async Tier 1 with lazy workspace discovery (before sync tiers)
    # Per ADR-0109: Discovery triggers on first unregistered GID
    async_tier1_result = await _detect_tier1_project_membership_async(task, client)
    if async_tier1_result:
        return async_tier1_result

    # Tiers 2-3 (sync) - skip sync Tier 1 since async already handled it
    # Note: We call detect_entity_type which internally does Tier 1 again,
    # but it will hit the static registry (now possibly populated by discovery)
    result = detect_entity_type(task, parent_type)

    # If we found a type (not UNKNOWN), return it
    if result:
        return result

    # Tier 4: Structure inspection (with cache integration)
    if allow_structure_inspection:
        # Per FR-CACHE-001: Check cache BEFORE Tier 4 API call
        # Per FR-CACHE-003: Cache check occurs AFTER Tiers 1-3
        # Per FR-DEGRADE-004: Handle None cache gracefully
        cache = getattr(client, "_cache_provider", None)

        if cache is not None:
            try:
                cached_result = _get_cached_detection(task.gid, cache)
                if cached_result is not None:
                    # Per FR-OBSERVE-001: Log cache hit
                    logger.info(
                        "detection_cache_hit",
                        extra={
                            "event": "detection_cache_hit",
                            "task_gid": task.gid,
                            "entity_type": cached_result.entity_type.value,
                            "tier_used": cached_result.tier_used,
                        },
                    )
                    return cached_result
                else:
                    # Per FR-OBSERVE-002: Log cache miss
                    logger.debug(
                        "detection_cache_miss",
                        extra={
                            "event": "detection_cache_miss",
                            "task_gid": task.gid,
                        },
                    )
            except CACHE_TRANSIENT_ERRORS as exc:
                # Per FR-DEGRADE-003: Log warning on cache failure
                logger.warning(
                    "detection_cache_check_failed",
                    extra={
                        "event": "detection_cache_check_failed",
                        "task_gid": task.gid,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )

        # Execute Tier 4 API call
        tier4_result = await detect_by_structure_inspection(task, client)

        if tier4_result is not None:
            # Per FR-CACHE-002: Cache successful Tier 4 result
            if cache is not None:
                try:
                    _cache_detection_result(task, tier4_result, cache)
                    # Per FR-OBSERVE-003: Log cache store
                    logger.info(
                        "detection_cache_store",
                        extra={
                            "event": "detection_cache_store",
                            "task_gid": task.gid,
                            "entity_type": tier4_result.entity_type.value,
                        },
                    )
                except CACHE_TRANSIENT_ERRORS as exc:
                    # Per FR-DEGRADE-003: Log warning on cache failure
                    logger.warning(
                        "detection_cache_store_failed",
                        extra={
                            "event": "detection_cache_store_failed",
                            "task_gid": task.gid,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
            return tier4_result

    # Tier 5: Unknown (already returned by detect_entity_type)
    return result


# --- Holder Identification ---


def identify_holder_type(
    task: Task,
    holder_key_map: dict[str, tuple[str, str]],
    *,
    filter_to_map: bool = False,
) -> str | None:
    """Identify which holder type a task is.

    Per TDD-SPRINT-1 Phase 2: Extracted utility for holder identification.
    Per ADR-0119: Consolidates Business._identify_holder and Unit._identify_holder.

    Uses detection system first (Tier 1: project membership, Tier 2: name patterns),
    falls back to legacy HOLDER_KEY_MAP matching with logged warning.

    Args:
        task: Task to identify.
        holder_key_map: Map of holder_key -> (name_pattern, emoji).
            Used for fallback matching when detection fails.
        filter_to_map: If True, only return holder keys present in holder_key_map.
            Used by Unit to filter to Unit-level holders (offer_holder, process_holder).
            If False, returns any detected holder type.

    Returns:
        Holder key name (e.g., "contact_holder") or None if not a holder.

    Example:
        >>> holder_key = identify_holder_type(
        ...     task,
        ...     Business.HOLDER_KEY_MAP,
        ...     filter_to_map=False,
        ... )
        >>> if holder_key:
        ...     print(f"Detected holder: {holder_key}")
    """
    # Try detection system first (Tier 1: project membership, Tier 2: name patterns)
    result = detect_entity_type(task)

    if result and result.entity_type.name.endswith("_HOLDER"):
        # Detection succeeded - map EntityType to holder key
        holder_attr = get_holder_attr(result.entity_type)
        if holder_attr:
            # Convert "_contact_holder" to "contact_holder"
            holder_key = holder_attr.lstrip("_")
            # Filter to map keys if requested (Unit-level holders only)
            if filter_to_map and holder_key not in holder_key_map:
                return None
            return holder_key

    # Fallback to legacy HOLDER_KEY_MAP matching
    for key, (name_pattern, emoji) in holder_key_map.items():
        if _matches_holder_pattern(task, name_pattern, emoji):
            logger.warning(
                "detection_fallback_holder_key_map",
                holder_key=key,
                task_name=task.name,
                task_gid=task.gid,
                fallback="HOLDER_KEY_MAP",
            )
            return key
    return None


def _matches_holder_pattern(task: Task, name_pattern: str, emoji: str) -> bool:
    """Check if task matches a holder definition.

    Per TDD-SPRINT-1 Phase 2: Extracted from Business._matches_holder.

    Uses suffix/contains matching for flexibility:
    - Exact match: "Contacts" == "contacts"
    - Suffix match: "My Contacts" ends with "contacts"
    - Contains match: "All Contacts Here" contains "contacts"

    Args:
        task: Task to check.
        name_pattern: Expected task name or pattern.
        emoji: Expected custom emoji name (currently unused).

    Returns:
        True if task matches holder pattern.
    """
    if not task.name:
        return False

    task_name_lower = task.name.lower()
    pattern_lower = name_pattern.lower()

    # Check exact match first
    if task_name_lower == pattern_lower:
        return True

    # Check suffix match (e.g., "My Contacts" ends with "contacts")
    if task_name_lower.endswith(pattern_lower):
        return True

    # Check contains match (e.g., "All Contacts Here" contains "contacts")
    # Fall back to emoji (not currently implemented in Task model)
    # Would check task.custom_emoji.name == emoji if available
    return pattern_lower in task_name_lower
