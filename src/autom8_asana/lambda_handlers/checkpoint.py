"""Checkpoint persistence for Lambda cache warmer resume capability.

Per TDD-lambda-cache-warmer and ADR-0064:
S3-based checkpoint persistence enabling resume-on-retry when Lambda
times out during cache warming. Checkpoints have a configurable staleness
window (default 1 hour) after which they are ignored.

Key: s3://{bucket}/cache-warmer/checkpoints/latest.json

Environment Variables:
    ASANA_CACHE_S3_BUCKET: S3 bucket for checkpoint storage (default: autom8-s3)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger = get_logger(__name__)

# Default configuration
DEFAULT_BUCKET = "autom8-s3"
DEFAULT_PREFIX = "cache-warmer/checkpoints/"
DEFAULT_STALENESS_HOURS = 1.0


def _default_bucket() -> str:
    """Resolve S3 bucket from settings with fallback to DEFAULT_BUCKET."""
    from autom8_asana.settings import get_settings

    return get_settings().s3.bucket or DEFAULT_BUCKET


@dataclass
class CheckpointRecord:
    """Checkpoint for resuming partial warming runs.

    Persisted to S3 at: s3://{bucket}/cache-warmer/checkpoints/latest.json

    Staleness window: configurable, default 1 hour from created_at.
    Checkpoints older than the staleness window are ignored and warming
    restarts from scratch.

    Attributes:
        invocation_id: Lambda request ID for correlation.
        completed_entities: Entity types successfully warmed.
        pending_entities: Entity types not yet processed.
        entity_results: WarmStatus.to_dict() for each completed entity.
        created_at: Checkpoint creation time (UTC).
        expires_at: Staleness expiration time (created_at + staleness window).
    """

    invocation_id: str
    completed_entities: list[str]
    pending_entities: list[str]
    entity_results: list[dict[str, Any]]
    created_at: datetime
    expires_at: datetime

    def is_stale(self) -> bool:
        """Check if checkpoint has exceeded staleness window.

        Returns:
            True if current time exceeds expires_at, False otherwise.
        """
        return datetime.now(UTC) > self.expires_at

    def to_json(self) -> str:
        """Serialize to JSON for S3 storage.

        Returns:
            JSON string representation of the checkpoint.
        """
        return json.dumps(
            {
                "invocation_id": self.invocation_id,
                "completed_entities": self.completed_entities,
                "pending_entities": self.pending_entities,
                "entity_results": self.entity_results,
                "created_at": self.created_at.isoformat(),
                "expires_at": self.expires_at.isoformat(),
            }
        )

    @classmethod
    def from_json(cls, data: str) -> CheckpointRecord:
        """Deserialize from JSON.

        Args:
            data: JSON string to parse.

        Returns:
            CheckpointRecord instance.

        Raises:
            json.JSONDecodeError: If data is not valid JSON.
            KeyError: If required fields are missing.
            ValueError: If datetime fields cannot be parsed.
        """
        obj = json.loads(data)

        # Parse datetime fields
        created_at = datetime.fromisoformat(obj["created_at"])
        expires_at = datetime.fromisoformat(obj["expires_at"])

        # Ensure timezone awareness
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        return cls(
            invocation_id=obj["invocation_id"],
            completed_entities=obj["completed_entities"],
            pending_entities=obj["pending_entities"],
            entity_results=obj["entity_results"],
            created_at=created_at,
            expires_at=expires_at,
        )


@dataclass
class CheckpointManager:
    """Manages checkpoint persistence to S3.

    Per ADR-0064: Uses S3 object storage for checkpoint persistence.
    Checkpoints are stored at a well-known S3 key for resumption.
    Only one checkpoint exists at a time (latest state).

    Thread Safety:
        Single writer is enforced by Lambda reserved_concurrent_executions=1.
        No race conditions expected in normal operation.

    Attributes:
        bucket: S3 bucket name for checkpoint storage.
        prefix: S3 key prefix (default: "cache-warmer/checkpoints/").
        s3_client: Injected S3 client (for testing). Created lazily if None.
        staleness_hours: Hours after which checkpoint is considered stale.

    Example:
        >>> mgr = CheckpointManager(bucket="autom8-s3")
        >>> await mgr.save_async(
        ...     invocation_id="abc-123",
        ...     completed_entities=["unit"],
        ...     pending_entities=["business", "offer"],
        ...     entity_results=[{"entity_type": "unit", "result": "success"}],
        ... )
        >>> checkpoint = await mgr.load_async()
        >>> if checkpoint and not checkpoint.is_stale():
        ...     print(f"Resuming from: {checkpoint.completed_entities}")
    """

    bucket: str = field(default_factory=_default_bucket)
    prefix: str = DEFAULT_PREFIX
    s3_client: S3Client | None = None
    staleness_hours: float = DEFAULT_STALENESS_HOURS

    def _ensure_client(self) -> S3Client:
        """Lazily initialize S3 client if not provided.

        Returns:
            Initialized S3 client.
        """
        if self.s3_client is None:
            import boto3

            self.s3_client = boto3.client("s3")
        return self.s3_client

    def _checkpoint_key(self) -> str:
        """Get the S3 key for the checkpoint file.

        Returns:
            Full S3 key path: {prefix}latest.json
        """
        return f"{self.prefix}latest.json"

    async def load_async(self) -> CheckpointRecord | None:
        """Load checkpoint if exists and fresh.

        Retrieves the checkpoint from S3 and checks staleness.
        Returns None if:
        - No checkpoint exists
        - Checkpoint is stale (exceeded staleness window)
        - S3 read fails (logged as warning, graceful degradation)

        Returns:
            CheckpointRecord if found and not stale, None otherwise.
        """
        client = self._ensure_client()
        key = self._checkpoint_key()

        try:
            response = client.get_object(Bucket=self.bucket, Key=key)
            data = response["Body"].read().decode("utf-8")
            checkpoint = CheckpointRecord.from_json(data)

            if checkpoint.is_stale():
                logger.info(
                    "checkpoint_stale",
                    extra={
                        "created_at": checkpoint.created_at.isoformat(),
                        "expires_at": checkpoint.expires_at.isoformat(),
                        "invocation_id": checkpoint.invocation_id,
                    },
                )
                return None

            logger.info(
                "checkpoint_loaded",
                extra={
                    "invocation_id": checkpoint.invocation_id,
                    "completed": checkpoint.completed_entities,
                    "pending": checkpoint.pending_entities,
                },
            )
            return checkpoint

        except client.exceptions.NoSuchKey:
            logger.debug(
                "checkpoint_not_found",
                extra={"bucket": self.bucket, "key": key},
            )
            return None

        except (
            Exception
        ) as e:  # BROAD-CATCH: catch-all-and-degrade -- S3 errors should not block warming
            # Graceful degradation: log warning and return None
            # Per ADR-0064: S3 errors should not block warming
            logger.warning(
                "checkpoint_load_error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "bucket": self.bucket,
                    "key": key,
                },
            )
            return None

    async def save_async(
        self,
        invocation_id: str,
        completed_entities: list[str],
        pending_entities: list[str],
        entity_results: list[dict[str, Any]],
    ) -> bool:
        """Save checkpoint to S3.

        Creates a new checkpoint record with the current timestamp and
        staleness expiration, then persists to S3.

        Args:
            invocation_id: Lambda request ID for correlation.
            completed_entities: Successfully warmed entity types.
            pending_entities: Entity types not yet processed.
            entity_results: WarmStatus dictionaries for completed entities.

        Returns:
            True on success, False on failure.
        """
        client = self._ensure_client()
        key = self._checkpoint_key()

        now = datetime.now(UTC)
        checkpoint = CheckpointRecord(
            invocation_id=invocation_id,
            completed_entities=completed_entities,
            pending_entities=pending_entities,
            entity_results=entity_results,
            created_at=now,
            expires_at=now + timedelta(hours=self.staleness_hours),
        )

        try:
            client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=checkpoint.to_json().encode("utf-8"),
                ContentType="application/json",
            )

            logger.info(
                "checkpoint_saved",
                extra={
                    "invocation_id": invocation_id,
                    "completed": completed_entities,
                    "pending": pending_entities,
                    "expires_at": checkpoint.expires_at.isoformat(),
                },
            )
            return True

        except Exception as e:  # BROAD-CATCH: isolation -- checkpoint save failure returns False, does not propagate
            logger.error(
                "checkpoint_save_error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "bucket": self.bucket,
                    "key": key,
                },
            )
            return False

    async def clear_async(self) -> bool:
        """Clear checkpoint after successful completion.

        Deletes the checkpoint from S3. Called when all entity types
        have been warmed successfully.

        Returns:
            True on success, False on failure.
        """
        client = self._ensure_client()
        key = self._checkpoint_key()

        try:
            client.delete_object(Bucket=self.bucket, Key=key)

            logger.info(
                "checkpoint_cleared",
                extra={"bucket": self.bucket, "key": key},
            )
            return True

        except Exception as e:  # BROAD-CATCH: isolation -- checkpoint clear failure returns False, expires naturally
            # Log warning but don't fail - checkpoint will expire naturally
            logger.warning(
                "checkpoint_clear_error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "bucket": self.bucket,
                    "key": key,
                },
            )
            return False
