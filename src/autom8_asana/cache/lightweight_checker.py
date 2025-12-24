"""Lightweight staleness checker using batch modified_at queries.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Performs batch modified_at checks via
Asana Batch API with minimal payload (opt_fields=modified_at).

Per FR-STALE-002: Uses opt_fields=modified_at for minimal payload.
Per FR-BATCH-003: Chunks into groups of 10 (Asana batch limit).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.cache.entry import CacheEntry

from autom8_asana.batch.models import BatchRequest

logger = logging.getLogger(__name__)

# Asana batch API limit per request
ASANA_BATCH_LIMIT = 10


@dataclass
class LightweightChecker:
    """Performs batch modified_at checks via Asana Batch API.

    Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Uses GET /tasks/{gid}?opt_fields=modified_at
    to check multiple tasks in a single batch request.

    Per FR-STALE-002: Minimal payload with opt_fields=modified_at.
    Per FR-BATCH-003: Chunks into groups of 10 (Asana limit).
    Per FR-DEGRADE-002/003: Handles partial batch failures gracefully.

    Attributes:
        batch_client: BatchClient for executing batch requests.
        chunk_size: Maximum actions per batch request (default 10, Asana limit).
    """

    batch_client: "BatchClient"
    chunk_size: int = ASANA_BATCH_LIMIT
    _total_checks: int = field(default=0, init=False, repr=False)
    _total_api_calls: int = field(default=0, init=False, repr=False)

    async def check_batch_async(
        self,
        entries: list["CacheEntry"],
    ) -> dict[str, str | None]:
        """Check modified_at for multiple entries via batch API.

        Per FR-STALE-002: Builds batch requests with opt_fields=modified_at.
        Per FR-BATCH-003: Chunks into groups of chunk_size (10 by default).
        Per FR-DEGRADE-003: Returns None for failed/malformed responses.

        Args:
            entries: Cache entries to check (TASK entries only).

        Returns:
            Dict mapping GID to modified_at string, or None if error/deleted.
            - modified_at string if successfully retrieved
            - None if 404 (deleted), error, or malformed response

        Example:
            >>> checker = LightweightChecker(batch_client=client)
            >>> entries = [entry1, entry2, entry3]
            >>> results = await checker.check_batch_async(entries)
            >>> results
            {"1234": "2025-12-23T10:30:00.000Z", "5678": None, "9012": "2025-12-24T08:15:00.000Z"}
        """
        if not entries:
            return {}

        results: dict[str, str | None] = {}
        gids = [e.key for e in entries]

        # Log batch start
        chunk_count = (len(gids) + self.chunk_size - 1) // self.chunk_size
        logger.debug(
            "lightweight_check_batch_start",
            extra={
                "cache_operation": "staleness_check",
                "batch_size": len(gids),
                "chunk_count": chunk_count,
            },
        )

        # Chunk and execute
        for chunk_gids in _chunk(gids, self.chunk_size):
            chunk_results = await self._check_chunk(chunk_gids)
            results.update(chunk_results)
            self._total_api_calls += 1

        self._total_checks += len(gids)

        # Log batch completion
        succeeded = sum(1 for v in results.values() if v is not None)
        logger.debug(
            "lightweight_check_batch_complete",
            extra={
                "cache_operation": "staleness_check",
                "batch_size": len(gids),
                "succeeded": succeeded,
                "failed_or_deleted": len(gids) - succeeded,
            },
        )

        return results

    async def _check_chunk(self, gids: list[str]) -> dict[str, str | None]:
        """Execute a single chunk of modified_at checks.

        Args:
            gids: GIDs to check in this chunk (max chunk_size).

        Returns:
            Dict mapping GID to modified_at or None.
        """
        requests = self._build_batch_requests(gids)

        try:
            batch_results = await self.batch_client.execute_async(requests)
            return self._parse_batch_response(batch_results, gids)
        except Exception as e:
            # Entire chunk failed - mark all as None
            logger.warning(
                "staleness_check_chunk_failure",
                extra={
                    "cache_operation": "staleness_check",
                    "chunk_size": len(gids),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return {gid: None for gid in gids}

    def _build_batch_requests(self, gids: list[str]) -> list[BatchRequest]:
        """Build batch GET requests for modified_at.

        Per TDD Appendix A: Uses GET /tasks/{gid} with opt_fields=modified_at.

        Args:
            gids: Task GIDs to check.

        Returns:
            List of BatchRequest objects.
        """
        return [
            BatchRequest(
                relative_path=f"/tasks/{gid}",
                method="GET",
                options={"opt_fields": "modified_at"},
            )
            for gid in gids
        ]

    def _parse_batch_response(
        self,
        results: list[Any],
        gids: list[str],
    ) -> dict[str, str | None]:
        """Parse batch results to modified_at mapping.

        Per FR-DEGRADE-002/003: Returns None for failed/malformed responses.

        Args:
            results: BatchResult objects from batch execution.
            gids: Original GIDs in request order.

        Returns:
            Dict mapping GID to modified_at string or None.
        """
        from autom8_asana.batch.models import BatchResult

        parsed: dict[str, str | None] = {}

        for i, result in enumerate(results):
            gid = gids[i] if i < len(gids) else None
            if gid is None:
                continue

            if isinstance(result, BatchResult):
                if result.success and result.data:
                    modified_at = result.data.get("modified_at")
                    if modified_at and isinstance(modified_at, str):
                        parsed[gid] = modified_at
                    else:
                        # Malformed response
                        logger.debug(
                            "staleness_check_malformed_response",
                            extra={
                                "cache_operation": "staleness_check",
                                "gid": gid,
                                "data": result.data,
                            },
                        )
                        parsed[gid] = None
                else:
                    # Failed or deleted
                    if result.status_code == 404:
                        logger.debug(
                            "staleness_check_entity_deleted",
                            extra={
                                "cache_operation": "staleness_check",
                                "gid": gid,
                                "status_code": 404,
                            },
                        )
                    else:
                        logger.warning(
                            "staleness_check_partial_failure",
                            extra={
                                "cache_operation": "staleness_check",
                                "gid": gid,
                                "status_code": result.status_code,
                                "error": str(result.error) if result.error else None,
                            },
                        )
                    parsed[gid] = None
            else:
                # Unexpected result type
                parsed[gid] = None

        return parsed

    def get_stats(self) -> dict[str, int]:
        """Get checker statistics.

        Returns:
            Dict with total_checks and total_api_calls.
        """
        return {
            "total_checks": self._total_checks,
            "total_api_calls": self._total_api_calls,
        }


def _chunk(items: list[str], size: int) -> list[list[str]]:
    """Split list into chunks of specified size.

    Args:
        items: List to chunk.
        size: Maximum chunk size.

    Returns:
        List of chunks.
    """
    if not items or size <= 0:
        return []
    return [items[i : i + size] for i in range(0, len(items), size)]
