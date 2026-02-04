# TDD: Unified DataFrame Persistence

**TDD ID**: TDD-UNIFIED-DF-PERSISTENCE-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**Sprint**: S4 (Architectural Opportunities -- Wave 4)
**Task**: S4-002 (B6)
**PRD Reference**: Architectural Opportunities Initiative
**Spike References**: S0-001 (Cache Baseline), S0-004 (Stale Data Analysis), S0-006 (Concurrent Build Analysis)
**Depends On**: C3 (RetryOrchestrator -- implemented), C1 (Exception Hierarchy -- implemented), B4 (Config Consolidation -- S3LocationConfig available)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Goals and Non-Goals](#3-goals-and-non-goals)
4. [Proposed Architecture](#4-proposed-architecture)
5. [Component Design: DataFrameStorage Protocol](#5-component-design-dataframestorage-protocol)
6. [Component Design: S3DataFrameStorage](#6-component-design-s3dataframestorage)
7. [Key Formatting Consolidation](#7-key-formatting-consolidation)
8. [RetryOrchestrator Integration](#8-retryorchestrator-integration)
9. [Async Strategy](#9-async-strategy)
10. [Configuration](#10-configuration)
11. [Migration Plan](#11-migration-plan)
12. [Module Placement](#12-module-placement)
13. [Interface Contracts](#13-interface-contracts)
14. [Data Flow Diagrams](#14-data-flow-diagrams)
15. [Non-Functional Considerations](#15-non-functional-considerations)
16. [Test Strategy](#16-test-strategy)
17. [Risk Assessment](#17-risk-assessment)
18. [ADRs](#18-adrs)
19. [Success Criteria](#19-success-criteria)

---

## 1. Overview

### 1.1 Problem Statement

The codebase contains three separate S3 persistence implementations that evolved independently, each with different retry semantics, error handling, configuration, and key formatting:

| Implementation | Location | Retry | Error Handling | Key Scheme | Config |
|----------------|----------|-------|----------------|------------|--------|
| **DataFramePersistence** | `dataframes/persistence.py` | None (bare `except S3_TRANSPORT_ERRORS`) | Custom `_handle_s3_error()` with degraded mode, manual reconnect timer | `{prefix}{project_gid}/dataframe.parquet` | `PersistenceConfig` dataclass |
| **AsyncS3Client** | `dataframes/async_s3.py` | Manual `for attempt in range(max_retries)` with exponential backoff | `DegradedModeMixin` + `is_s3_retryable_error()` from `cache/errors.py` | Caller-provided (raw key) | `AsyncS3Config` dataclass |
| **SectionPersistence** | `dataframes/section_persistence.py` | Delegates to `AsyncS3Client` (inherits its retry) | Result objects (`S3WriteResult`/`S3ReadResult`) + logging | `{prefix}{project_gid}/sections/{section_gid}.parquet` | `SectionPersistenceConfig` dataclass |

These three implementations share 80% of their concerns (S3 connectivity, parquet serialization, watermark JSON, degraded mode, error classification) but diverge on the 20% that matters most for operational reliability: retry coordination, error propagation, and failure recovery.

### 1.2 Divergence Analysis

**Retry Semantics:**
- `DataFramePersistence`: Zero retries. Any S3 error enters degraded mode immediately. Recovery depends on a 60-second reconnect timer.
- `AsyncS3Client`: 3 retries with 0.5s base exponential backoff. Classifies errors via `is_s3_retryable_error()`. No budget awareness.
- `SectionPersistence`: Inherits `AsyncS3Client` retry behavior but wraps results in `S3WriteResult`/`S3ReadResult`, losing the original exception context.

**Error Handling:**
- `DataFramePersistence`: Returns `bool` success/failure. Enters degraded mode on connection-class errors. Uses custom `_is_not_found_error()` with manual botocore introspection.
- `AsyncS3Client`: Returns result dataclasses. Uses `is_s3_not_found_error()` and `is_s3_retryable_error()` from `cache/models/errors.py`.
- `SectionPersistence`: Delegates to `AsyncS3Client` results. Logs failures but swallows errors.

**Configuration:**
- Three separate config dataclasses (`PersistenceConfig`, `AsyncS3Config`, `SectionPersistenceConfig`) all containing `bucket`, `region`, `endpoint_url`.
- All three independently resolve from Pydantic Settings with identical `get_settings().s3` patterns.
- `S3LocationConfig` (from B4) already exists as the consolidated primitive but is not yet used by any of these implementations.

**Key Formatting:**
- `DataFramePersistence` and `SectionPersistence` both generate keys for `dataframe.parquet`, `watermark.json`, and `gid_lookup_index.json` with identical logic but in separate methods.
- `SectionPersistence` adds `manifest.json` and `sections/{section_gid}.parquet` keys.
- `AsyncS3Client` is key-agnostic (raw key passthrough).

### 1.3 Solution Summary

A unified `DataFrameStorage` protocol with a single `S3DataFrameStorage` implementation that:

1. Consolidates all S3 persistence operations behind a single protocol
2. Uses `RetryOrchestrator` (from C3) for coordinated retry with budget enforcement
3. Uses `S3LocationConfig` (from B4) for configuration
4. Uses `S3TransportError` (from C1) for error classification
5. Provides both sync-compatible and async interfaces via `asyncio.to_thread()`

---

## 2. Problem Statement

### 2.1 Operational Impact

The divergent retry strategies create unpredictable behavior during S3 degradation:

```
Scenario: S3 returns intermittent 500 errors (50% failure rate)

Path A (via DataFramePersistence.load_dataframe):
  Attempt 1: FAIL -> immediate degraded mode -> return None
  No retry. Data unavailable until 60s reconnect timer.

Path B (via SectionPersistence.write_section_async -> AsyncS3Client):
  Attempt 1: FAIL -> retry after 0.5s
  Attempt 2: FAIL -> retry after 1.0s
  Attempt 3: SUCCESS -> data persisted
  Wall time: ~1.5s. Data available.

Same S3 outage, same bucket, different outcomes depending on code path.
```

When both paths operate concurrently during a build, `DataFramePersistence` enters degraded mode and stops loading project-level data, while `SectionPersistence` continues writing sections through transient errors. The result is a build that writes sections successfully but cannot read the final merged DataFrame -- a consistency gap that requires manual intervention.

### 2.2 Maintenance Burden

Bug fixes and improvements must be applied to three locations:
- Adding `RetryOrchestrator` support requires modifying all three classes
- Adding new S3 object types (e.g., metrics snapshots) means choosing which of three patterns to follow
- Error handling improvements (like the C1 exception hierarchy integration) must be replicated three times

---

## 3. Goals and Non-Goals

### 3.1 Goals

1. **Single S3 interface**: One protocol (`DataFrameStorage`) defining all DataFrame persistence operations.
2. **Unified retry**: All S3 operations routed through `RetryOrchestrator` with `Subsystem.S3` budget.
3. **Unified error handling**: All S3 errors wrapped as `S3TransportError` at the boundary, using `S3TransportError.from_boto_error()`.
4. **Unified configuration**: `S3LocationConfig` as the single config source for bucket/region/endpoint.
5. **Backward compatibility**: Existing consumers (`WatermarkRepository`, `SectionPersistence`, builder pipeline) continue working with minimal changes.
6. **Preserve all capabilities**: Parquet format, watermark persistence, GidLookupIndex persistence, section-level persistence, manifest tracking, checkpoint operations.

### 3.2 Non-Goals

- Changing the S3 key structure (keys remain backward compatible with existing persisted data).
- Implementing a new storage backend (e.g., DynamoDB). The protocol enables this but we only implement S3.
- Modifying the `SectionManifest` model or section lifecycle (those concerns remain in `SectionPersistence`).
- Replacing `asyncio.to_thread()` with a native async S3 client (aioboto3 etc.).
- Adding encryption, compression, or versioning to persisted objects.

### 3.3 Constraints

- Must not break existing S3 key layouts. Persisted data from before migration must remain readable.
- Python 3.11+.
- `RetryOrchestrator` (C3) must be the sole retry mechanism. No manual retry loops.
- `S3LocationConfig` (B4) must be the sole config source for S3 location.

---

## 4. Proposed Architecture

### 4.1 Layered Design

```
                         Consumers
                  (WatermarkRepository, builders,
                   SectionPersistence, API startup)
                              |
                              v
                    +-----------------------+
                    |  DataFrameStorage     |   <-- Protocol
                    |  (Protocol)           |
                    +-----------------------+
                              |
                              v
                    +-----------------------+
                    |  S3DataFrameStorage   |   <-- Single implementation
                    |                       |
                    |  - parquet I/O        |
                    |  - watermark I/O      |
                    |  - index I/O          |
                    |  - section I/O        |
                    |  - manifest I/O       |
                    |  - key formatting     |
                    +-----------------------+
                        |             |
                        v             v
              +----------------+  +-------------------+
              | RetryOrchest-  |  | boto3 S3 Client   |
              | rator (S3)     |  | (via to_thread)   |
              +----------------+  +-------------------+
                        |
                        v
              +----------------+
              | RetryBudget    |  <-- Shared with Redis, HTTP
              | (global)       |
              +----------------+
```

### 4.2 What Gets Replaced

| Current | Replacement | Migration |
|---------|-------------|-----------|
| `DataFramePersistence` (994 lines) | `S3DataFrameStorage` | Thin wrapper during transition, then direct replacement |
| `AsyncS3Client` (625 lines) | Internal detail of `S3DataFrameStorage` (raw put/get methods) | `SectionPersistence` rewired to use `S3DataFrameStorage` |
| `AsyncS3Config` | `S3LocationConfig` + storage-level config | Config replaced |
| `PersistenceConfig` | `S3LocationConfig` + storage-level config | Config replaced |
| `SectionPersistenceConfig` | `S3LocationConfig` | Config replaced |

### 4.3 What Stays

| Component | Reason |
|-----------|--------|
| `SectionPersistence` class | Owns section lifecycle, manifest logic, checkpoint coordination -- these are domain concerns above storage |
| `SectionManifest` / `SectionInfo` models | Data models, not storage |
| `S3WriteResult` / `S3ReadResult` | Useful result types, retained as return types from storage operations |
| `TaskCacheCoordinator` | Operates on cache layer, not S3 persistence layer |

---

## 5. Component Design: DataFrameStorage Protocol

### 5.1 Protocol Definition

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

import polars as pl


@runtime_checkable
class DataFrameStorage(Protocol):
    """Protocol for DataFrame persistence operations.

    Defines the complete interface for persisting and retrieving DataFrames,
    watermarks, GidLookupIndex data, and section-level parquet files to a
    storage backend.
    """

    # ---- Availability ----

    @property
    def is_available(self) -> bool:
        """Whether the storage backend is currently healthy."""
        ...

    # ---- DataFrame operations ----

    async def save_dataframe(
        self,
        project_gid: str,
        df: pl.DataFrame,
        watermark: datetime,
        *,
        entity_type: str | None = None,
    ) -> bool:
        """Persist DataFrame and watermark atomically."""
        ...

    async def load_dataframe(
        self,
        project_gid: str,
    ) -> tuple[pl.DataFrame | None, datetime | None]:
        """Load DataFrame and watermark. Returns (None, None) if not found."""
        ...

    async def delete_dataframe(self, project_gid: str) -> bool:
        """Delete DataFrame, watermark, and index for a project."""
        ...

    # ---- Watermark operations ----

    async def save_watermark(self, project_gid: str, watermark: datetime) -> bool:
        """Persist watermark only (lightweight write-through)."""
        ...

    async def get_watermark(self, project_gid: str) -> datetime | None:
        """Get watermark without loading DataFrame."""
        ...

    async def load_all_watermarks(self) -> dict[str, datetime]:
        """Bulk load all watermarks (startup hydration)."""
        ...

    # ---- GidLookupIndex operations ----

    async def save_index(
        self, project_gid: str, index_data: dict[str, Any]
    ) -> bool:
        """Persist serialized GidLookupIndex."""
        ...

    async def load_index(self, project_gid: str) -> dict[str, Any] | None:
        """Load serialized GidLookupIndex."""
        ...

    async def delete_index(self, project_gid: str) -> bool:
        """Delete GidLookupIndex."""
        ...

    # ---- Section operations ----

    async def save_section(
        self,
        project_gid: str,
        section_gid: str,
        df: pl.DataFrame,
        *,
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """Persist a section-level parquet file."""
        ...

    async def load_section(
        self,
        project_gid: str,
        section_gid: str,
    ) -> pl.DataFrame | None:
        """Load a section-level parquet file."""
        ...

    async def delete_section(
        self, project_gid: str, section_gid: str
    ) -> bool:
        """Delete a section-level parquet file."""
        ...

    # ---- Raw object operations (for manifests, etc.) ----

    async def save_json(self, key: str, data: bytes) -> bool:
        """Write raw JSON bytes to a key."""
        ...

    async def load_json(self, key: str) -> bytes | None:
        """Read raw bytes from a key. Returns None if not found."""
        ...

    async def delete_object(self, key: str) -> bool:
        """Delete a single object by key."""
        ...

    # ---- Enumeration ----

    async def list_projects(self) -> list[str]:
        """List all project GIDs with persisted data."""
        ...
```

### 5.2 Design Decisions

**Index serialization at the protocol boundary.** The protocol accepts `dict[str, Any]` for index operations rather than `GidLookupIndex` directly. This avoids coupling the storage protocol to the `services.gid_lookup` module and keeps serialization/deserialization in the consumer. The current `DataFramePersistence.save_index()` already calls `index.serialize()` before storage -- we just move that call to the consumer.

**Section operations in the protocol.** Rather than having `SectionPersistence` own its own S3 client, section parquet I/O is part of the storage protocol. `SectionPersistence` retains manifest lifecycle and checkpoint coordination but delegates raw S3 I/O to the storage implementation. This eliminates the second boto3 client instance.

**Raw JSON operations.** Manifest persistence needs arbitrary key read/write that does not map to the DataFrame/watermark/index pattern. The `save_json`/`load_json`/`delete_object` methods provide this without SectionPersistence needing direct S3 access.

---

## 6. Component Design: S3DataFrameStorage

### 6.1 Class Structure

```python
class S3DataFrameStorage:
    """S3 implementation of DataFrameStorage protocol.

    Consolidates DataFramePersistence, AsyncS3Client, and the S3 I/O
    portions of SectionPersistence into a single implementation with:
    - RetryOrchestrator for coordinated retry with budget enforcement
    - S3LocationConfig for configuration
    - S3TransportError for error classification
    - asyncio.to_thread() for non-blocking I/O
    """

    def __init__(
        self,
        location: S3LocationConfig,
        *,
        prefix: str = "dataframes/",
        retry_orchestrator: RetryOrchestrator | None = None,
        enabled: bool = True,
    ) -> None: ...
```

### 6.2 Internal Architecture

```
S3DataFrameStorage
|
+-- _location: S3LocationConfig         # bucket/region/endpoint
+-- _prefix: str                         # "dataframes/"
+-- _retry: RetryOrchestrator           # C3 orchestrator (Subsystem.S3)
+-- _client: boto3.S3Client | None      # Lazy-initialized, thread-safe
+-- _client_lock: threading.Lock        # Protects client initialization
+-- _degraded: bool                     # Degraded mode flag
|
+-- Key formatting methods (consolidated):
|   +-- _df_key(project_gid) -> str
|   +-- _watermark_key(project_gid) -> str
|   +-- _index_key(project_gid) -> str
|   +-- _section_key(project_gid, section_gid) -> str
|   +-- _manifest_key(project_gid) -> str
|
+-- Core S3 operations (all go through RetryOrchestrator):
|   +-- _put_object(key, body, content_type, metadata) -> bool
|   +-- _get_object(key) -> bytes | None
|   +-- _delete_object(key) -> bool
|   +-- _list_common_prefixes(prefix) -> list[str]
|
+-- Serialization helpers:
    +-- _serialize_parquet(df) -> bytes
    +-- _deserialize_parquet(data) -> pl.DataFrame
    +-- _serialize_watermark(project_gid, watermark, df, entity_type) -> bytes
    +-- _deserialize_watermark(data) -> datetime
```

### 6.3 Core S3 Operation Pattern

Every S3 call follows this pattern:

```python
async def _put_object(
    self,
    key: str,
    body: bytes,
    content_type: str = "application/octet-stream",
    metadata: dict[str, str] | None = None,
) -> bool:
    """Write object to S3 via RetryOrchestrator."""
    if self._degraded:
        return False

    try:
        client = self._get_client()

        def _do_put() -> None:
            put_kwargs: dict[str, Any] = {
                "Bucket": self._location.bucket,
                "Key": key,
                "Body": body,
                "ContentType": content_type,
            }
            if metadata:
                put_kwargs["Metadata"] = metadata
            client.put_object(**put_kwargs)

        # RetryOrchestrator handles retry, budget, circuit breaker
        await self._retry.execute_with_retry_async(
            lambda: asyncio.to_thread(_do_put),
            operation_name=f"s3_put:{key}",
        )
        return True

    except CircuitBreakerOpenError:
        logger.warning("s3_circuit_open", key=key)
        self._degraded = True
        return False
    except S3_TRANSPORT_ERRORS as e:
        wrapped = S3TransportError.from_boto_error(
            e, operation="put_object", bucket=self._location.bucket, key=key
        )
        if not wrapped.transient:
            self._degraded = True
        logger.error("s3_put_failed", key=key, error=str(wrapped))
        return False
```

### 6.4 Degraded Mode

The implementation uses a simplified degraded mode compared to the three current implementations:

- **Entry**: Circuit breaker opens (via RetryOrchestrator exhaustion) or permanent S3 error (AccessDenied, NoSuchBucket).
- **Recovery**: Automatic via circuit breaker half-open probe. No manual reconnect timer.
- **Behavior while degraded**: All operations return failure immediately (no S3 calls). Circuit breaker recovery_timeout (default 60s) controls when probes begin.

This replaces three different degraded mode implementations:
- `DataFramePersistence._attempt_reconnect()` with 60s timer
- `AsyncS3Client._get_client()` with `_last_error_time` check
- `DegradedModeMixin.enter_degraded_mode()` / `exit_degraded_mode()`

### 6.5 Async Context Manager

```python
async def __aenter__(self) -> S3DataFrameStorage:
    """Initialize boto3 client."""
    await self._ensure_initialized()
    return self

async def __aexit__(self, *args) -> None:
    """Release resources."""
    self._client = None
```

The context manager is optional. Lazy initialization in `_get_client()` handles the case where the storage is used without `async with`.

---

## 7. Key Formatting Consolidation

### 7.1 Current Key Schemes (Verified Identical)

All three implementations use the same key structure:

```
{prefix}{project_gid}/dataframe.parquet
{prefix}{project_gid}/watermark.json
{prefix}{project_gid}/gid_lookup_index.json
{prefix}{project_gid}/manifest.json              (SectionPersistence only)
{prefix}{project_gid}/sections/{section_gid}.parquet  (SectionPersistence only)
```

Default prefix is `"dataframes/"` in all three.

### 7.2 Consolidated Key Methods

```python
def _df_key(self, project_gid: str) -> str:
    return f"{self._prefix}{project_gid}/dataframe.parquet"

def _watermark_key(self, project_gid: str) -> str:
    return f"{self._prefix}{project_gid}/watermark.json"

def _index_key(self, project_gid: str) -> str:
    return f"{self._prefix}{project_gid}/gid_lookup_index.json"

def _section_key(self, project_gid: str, section_gid: str) -> str:
    return f"{self._prefix}{project_gid}/sections/{section_gid}.parquet"

def _manifest_key(self, project_gid: str) -> str:
    return f"{self._prefix}{project_gid}/manifest.json"
```

No migration needed for existing S3 data -- keys are identical.

---

## 8. RetryOrchestrator Integration

### 8.1 Orchestrator Configuration for S3

```python
from autom8_asana.core.retry import (
    BackoffType,
    BudgetConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    DefaultRetryPolicy,
    RetryBudget,
    RetryOrchestrator,
    RetryPolicyConfig,
    Subsystem,
)

def create_s3_retry_orchestrator(
    budget: RetryBudget | None = None,
) -> RetryOrchestrator:
    """Create a RetryOrchestrator configured for S3 persistence operations.

    Args:
        budget: Shared retry budget. If None, creates a standalone budget.
            In production, pass the application-wide shared budget.

    Returns:
        Configured RetryOrchestrator for Subsystem.S3.
    """
    policy = DefaultRetryPolicy(RetryPolicyConfig(
        backoff_type=BackoffType.EXPONENTIAL,
        max_attempts=3,
        base_delay=0.5,
        max_delay=10.0,
        jitter=True,
    ))

    if budget is None:
        budget = RetryBudget(BudgetConfig(
            per_subsystem_max=20,
            global_max=50,
            window_seconds=60.0,
        ))

    circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        half_open_max_probes=2,
        name="s3-dataframe-storage",
    ))

    return RetryOrchestrator(
        policy=policy,
        budget=budget,
        circuit_breaker=circuit_breaker,
        subsystem=Subsystem.S3,
    )
```

### 8.2 Retry Flow

```
Consumer calls: await storage.save_dataframe("proj_123", df, watermark)
    |
    +-- S3DataFrameStorage._put_object(key, parquet_bytes)
        |
        +-- RetryOrchestrator.execute_with_retry_async(lambda: to_thread(put))
            |
            +-- Attempt 1: CircuitBreaker.allow_request() -> True
            |   boto3 put_object() -> S3 500 error
            |   CircuitBreaker.record_failure()
            |   DefaultRetryPolicy.should_retry() -> True (transient)
            |   RetryBudget.try_acquire(S3) -> True (budget available)
            |   asyncio.sleep(0.5 * jitter)
            |
            +-- Attempt 2: CircuitBreaker.allow_request() -> True
            |   boto3 put_object() -> Success
            |   CircuitBreaker.record_success()
            |   RetryBudget.release(S3)
            |   Return
```

### 8.3 Budget Sharing

The `RetryBudget` instance should be shared across the application. When `S3DataFrameStorage` retries exhaust the S3 subsystem budget, subsequent S3 operations (including those from other code paths) fail fast instead of amplifying the outage.

Factory function `create_s3_retry_orchestrator(budget=shared_budget)` accepts an externally provided budget for this purpose. The `ServiceResolver` or dependency injection layer provides the shared budget.

---

## 9. Async Strategy

### 9.1 Decision: asyncio.to_thread()

Retain the `asyncio.to_thread()` approach from `AsyncS3Client`. This is proven in the codebase and matches AWS best practices.

```python
async def _put_object(self, key: str, body: bytes, ...) -> bool:
    def _sync_put():
        self._client.put_object(Bucket=..., Key=key, Body=body, ...)

    await self._retry.execute_with_retry_async(
        lambda: asyncio.to_thread(_sync_put),
        operation_name=f"s3_put:{key}",
    )
```

### 9.2 Thread Safety

- A single `boto3.client("s3")` instance is shared across all `to_thread()` calls. boto3 clients are thread-safe for S3 operations.
- Client creation is protected by `threading.Lock`.
- No shared mutable state beyond `_degraded` flag (reads are atomic for booleans in CPython).

---

## 10. Configuration

### 10.1 S3LocationConfig Usage

```python
from autom8_asana.config import S3LocationConfig

# From environment (production)
location = S3LocationConfig.from_env()

# Explicit (testing)
location = S3LocationConfig(
    bucket="test-bucket",
    region="us-east-1",
    endpoint_url="http://localhost:4566",
)

storage = S3DataFrameStorage(
    location=location,
    prefix="dataframes/",
    retry_orchestrator=orchestrator,
)
```

### 10.2 Storage-Level Config

Beyond `S3LocationConfig`, `S3DataFrameStorage` accepts:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prefix` | `"dataframes/"` | S3 key prefix for all objects |
| `retry_orchestrator` | Auto-created | RetryOrchestrator for S3 operations |
| `enabled` | `True` | Master enable/disable |
| `connect_timeout` | `10` | boto3 connection timeout (seconds) |
| `read_timeout` | `30` | boto3 read timeout (seconds) |

---

## 11. Migration Plan

### 11.1 Phase 1: Introduce S3DataFrameStorage (Non-Breaking)

**Scope**: Create `S3DataFrameStorage` class and `DataFrameStorage` protocol. No consumer changes.

**Files created:**
- `src/autom8_asana/dataframes/storage.py` -- Protocol + S3DataFrameStorage implementation
- `tests/unit/dataframes/test_storage.py` -- Unit tests

**Files modified:**
- None (purely additive)

### 11.2 Phase 2: Rewire SectionPersistence

**Goal**: Replace `AsyncS3Client` usage inside `SectionPersistence` with `S3DataFrameStorage`.

**Before:**
```python
class SectionPersistence:
    def __init__(self, ...):
        self._s3_client = AsyncS3Client(config=AsyncS3Config(...))

    async def write_section_async(self, ...):
        result = await self._s3_client.put_object_async(key, body, ...)
```

**After:**
```python
class SectionPersistence:
    def __init__(self, storage: DataFrameStorage, ...):
        self._storage = storage

    async def write_section_async(self, ...):
        return await self._storage.save_section(project_gid, section_gid, df, ...)
```

**Backward compatibility**: Constructor accepts either `storage` parameter (new path) or existing `bucket`/`config` parameters (creates `S3DataFrameStorage` internally). Deprecation warning on old path.

**Files modified:**
- `src/autom8_asana/dataframes/section_persistence.py`
- Tests that construct `SectionPersistence`

### 11.3 Phase 3: Rewire DataFramePersistence Consumers

**Goal**: Replace `DataFramePersistence` usage with `S3DataFrameStorage`.

**Consumers to migrate:**

| Consumer | File | Usage |
|----------|------|-------|
| `WatermarkRepository` | `dataframes/watermark.py` | `save_watermark`, `load_all_watermarks`, `get_watermark_only` |
| API startup preload | `api/main.py` | `load_dataframe`, `list_persisted_projects` |
| Cache warming script | `scripts/warm_cache.py` | `load_dataframe` |

**Strategy**: `DataFramePersistence` becomes a thin delegation wrapper:

```python
class DataFramePersistence:
    """Backward-compatible wrapper. Delegates to S3DataFrameStorage.

    .. deprecated::
        Use S3DataFrameStorage directly.
    """

    def __init__(self, ...):
        self._storage = S3DataFrameStorage(
            location=S3LocationConfig(...),
            prefix=prefix,
        )

    async def save_dataframe(self, project_gid, df, watermark):
        return await self._storage.save_dataframe(project_gid, df, watermark)

    # ... etc, all methods delegate
```

### 11.4 Phase 4: Remove Legacy Code

**After all consumers are migrated and tests pass:**

1. Remove `DataFramePersistence` class (replace with import alias or deprecation shim)
2. Remove `AsyncS3Client` class
3. Remove `PersistenceConfig`, `AsyncS3Config`, `SectionPersistenceConfig`
4. Remove `S3WriteResult`, `S3ReadResult` if no longer referenced externally

**Timeline estimate**: Phase 4 can be deferred. The delegation wrappers have near-zero overhead and provide a safe rollback path.

---

## 12. Module Placement

### 12.1 New Files

| File | Purpose |
|------|---------|
| `src/autom8_asana/dataframes/storage.py` | `DataFrameStorage` protocol + `S3DataFrameStorage` implementation |

### 12.2 Rationale

Placement in `dataframes/` (not `cache/` or `core/`) because:
- The primary concern is DataFrame persistence, not generic S3 access
- Existing consumers are in the `dataframes/` package
- `core/` is for truly cross-cutting utilities (exceptions, retry, schema)
- The protocol name `DataFrameStorage` makes the domain explicit

---

## 13. Interface Contracts

### 13.1 Save DataFrame

```python
async def save_dataframe(
    self,
    project_gid: str,
    df: pl.DataFrame,
    watermark: datetime,
    *,
    entity_type: str | None = None,
) -> bool:
```

**Contract:**
- `watermark` must be timezone-aware. Raises `ValueError` if naive.
- Writes both `dataframe.parquet` and `watermark.json` atomically (best-effort -- both are written but not transactionally).
- Returns `True` if both writes succeed, `False` if either fails.
- On failure, partial state is possible (parquet written, watermark not). Consumers must tolerate this.

### 13.2 Load DataFrame

```python
async def load_dataframe(
    self,
    project_gid: str,
) -> tuple[pl.DataFrame | None, datetime | None]:
```

**Contract:**
- Returns `(None, None)` if no data exists or on error.
- Loads watermark first (fast check), then DataFrame.
- If watermark exists but DataFrame is missing, returns `(None, None)` with a warning log.

### 13.3 Section Operations

```python
async def save_section(
    self,
    project_gid: str,
    section_gid: str,
    df: pl.DataFrame,
    *,
    metadata: dict[str, str] | None = None,
) -> bool:
```

**Contract:**
- Writes a single section parquet to `{prefix}{project_gid}/sections/{section_gid}.parquet`.
- Does NOT update manifests (that responsibility stays with `SectionPersistence`).
- Returns `True` on success.

---

## 14. Data Flow Diagrams

### 14.1 Save DataFrame Flow

```
Consumer
  |
  v
S3DataFrameStorage.save_dataframe(project_gid, df, watermark)
  |
  +-- Validate watermark is tz-aware
  |
  +-- _serialize_parquet(df) -> parquet_bytes
  |
  +-- _put_object(_df_key(project_gid), parquet_bytes, metadata={...})
  |     |
  |     +-- RetryOrchestrator.execute_with_retry_async()
  |           +-- asyncio.to_thread(boto3.put_object)
  |
  +-- _serialize_watermark(project_gid, watermark, df, entity_type) -> json_bytes
  |
  +-- _put_object(_watermark_key(project_gid), json_bytes)
  |     |
  |     +-- RetryOrchestrator.execute_with_retry_async()
  |           +-- asyncio.to_thread(boto3.put_object)
  |
  +-- Return True if both succeed
```

### 14.2 Section Persistence Integration

```
SectionPersistence.write_section_async(project_gid, section_gid, df)
  |
  +-- S3DataFrameStorage.save_section(project_gid, section_gid, df, metadata)
  |     |
  |     +-- _put_object(_section_key(...), parquet_bytes)
  |           +-- RetryOrchestrator handles retry
  |
  +-- SectionPersistence.update_manifest_section_async(...)
        |
        +-- S3DataFrameStorage.save_json(_manifest_key(...), manifest_json)
              +-- RetryOrchestrator handles retry
```

---

## 15. Non-Functional Considerations

### 15.1 Performance

**Expected impact: Neutral to positive.**

- Removing the second boto3 client instance (AsyncS3Client) reduces memory footprint by ~2MB per process.
- RetryOrchestrator adds negligible overhead on the happy path (two boolean checks: circuit breaker + budget).
- `asyncio.to_thread()` performance is unchanged.

**Benchmark targets:**
- Put object latency: < 100ms p50, < 500ms p95 (same as current AsyncS3Client)
- Get object latency: < 80ms p50, < 400ms p95
- Degraded mode entry: < 1ms (no S3 calls)

### 15.2 Reliability

- Circuit breaker prevents cascade amplification during S3 outages (same benefit as C3 for other subsystems).
- Shared budget prevents S3 retry storms from starving Redis or HTTP retries.
- Automatic recovery via half-open probes eliminates the need for manual degraded mode management.

### 15.3 Observability

Structured log events at each stage:

| Event | Level | Fields |
|-------|-------|--------|
| `s3_storage_initialized` | DEBUG | bucket, prefix, region |
| `s3_storage_put_success` | DEBUG | key, size_bytes, duration_ms |
| `s3_storage_get_success` | DEBUG | key, size_bytes, duration_ms |
| `s3_storage_not_found` | DEBUG | key |
| `s3_storage_error` | ERROR | key, operation, error, error_code |
| `s3_storage_degraded` | WARNING | reason, circuit_state |
| `s3_storage_recovered` | INFO | downtime_seconds |

RetryOrchestrator provides additional retry/budget/circuit-breaker events automatically.

---

## 16. Test Strategy

### 16.1 Unit Tests

**File**: `tests/unit/dataframes/test_storage.py`

| Test | Description |
|------|-------------|
| `test_save_dataframe_happy_path` | Verify parquet + watermark both written with correct keys |
| `test_save_dataframe_naive_watermark_raises` | ValueError on timezone-naive watermark |
| `test_load_dataframe_not_found` | Returns (None, None) when watermark missing |
| `test_load_dataframe_orphan_watermark` | Returns (None, None) when watermark exists but parquet missing |
| `test_save_section_key_format` | Verify section key includes sections/ subdirectory |
| `test_save_json_and_load_json_roundtrip` | Raw JSON operations for manifest support |
| `test_degraded_mode_skips_operations` | All operations return failure when degraded |
| `test_retry_on_transient_error` | Verify RetryOrchestrator is invoked for transient S3 errors |
| `test_circuit_breaker_opens_on_repeated_failure` | Degraded mode after threshold failures |
| `test_circuit_breaker_recovery` | Operations resume after half-open probe succeeds |
| `test_budget_exhaustion_fails_fast` | Operations fail when retry budget exhausted |
| `test_list_projects` | Verify project GID extraction from S3 common prefixes |
| `test_load_all_watermarks` | Bulk watermark loading |
| `test_is_available_reflects_client_state` | Property checks client + degraded state |
| `test_not_found_errors_not_retried` | NoSuchKey errors fail immediately, no retry |
| `test_permanent_errors_enter_degraded` | AccessDenied enters degraded mode |
| `test_enabled_false_disables_all_operations` | enabled=False returns failure for all ops |

### 16.2 Integration Tests

**File**: `tests/integration/test_s3_storage_e2e.py` (requires LocalStack)

| Test | Description |
|------|-------------|
| `test_dataframe_roundtrip` | Save and load DataFrame with watermark |
| `test_section_roundtrip` | Save and load section parquet |
| `test_index_roundtrip` | Save and load GidLookupIndex data |
| `test_delete_cascade` | Delete removes dataframe + watermark + index |

### 16.3 Migration Tests

Verify backward compatibility during Phases 2-3:

| Test | Description |
|------|-------------|
| `test_section_persistence_delegation` | SectionPersistence delegates S3 I/O to storage |
| `test_dataframe_persistence_wrapper` | DataFramePersistence wrapper produces identical behavior |
| `test_existing_s3_data_readable` | Data written by old implementation readable by new |

---

## 17. Risk Assessment

### 17.1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **R1**: Breaking existing S3 data compatibility | Low | High | Key format is identical. Integration test verifies old data is readable. |
| **R2**: SectionPersistence migration introduces subtle behavior change | Medium | Medium | Phase 2 runs both paths in parallel during testing. Result comparison tests. |
| **R3**: RetryOrchestrator adds latency on happy path | Low | Low | Two boolean checks (~10ns). Benchmark confirms neutral performance. |
| **R4**: Shared retry budget causes unrelated operations to fail fast | Medium | Medium | Budget is per-subsystem (S3: 20 tokens/60s). Only system-wide S3 storms trigger denial. Acceptable tradeoff. |
| **R5**: boto3 client thread safety assumption invalid | Low | High | Well-documented AWS behavior. Existing AsyncS3Client relies on same assumption successfully. |
| **R6**: Phase 4 (removal) breaks unknown consumers | Low | Medium | Phase 4 is optional and deferred. Deprecation warnings provide visibility. Grep for imports before removal. |

### 17.2 Rollback Strategy

Each phase is independently reversible:
- **Phase 1**: Delete new file. No consumers affected.
- **Phase 2**: Revert `SectionPersistence` constructor change. Old `AsyncS3Client` still exists.
- **Phase 3**: Revert delegation wrapper. Old `DataFramePersistence` still exists.
- **Phase 4**: Not attempted until Phases 1-3 are stable.

---

## 18. ADRs

### ADR-B6-001: Single Protocol over Multiple Thin Interfaces

**Context**: We could define separate protocols for DataFrame storage, section storage, and index storage, matching the current separation.

**Decision**: Single `DataFrameStorage` protocol covering all persistence operations.

**Rationale**:
- All operations target the same S3 bucket with the same configuration and retry semantics.
- Splitting into multiple protocols would require consumers that need both DataFrame and section operations to depend on multiple interfaces.
- The protocol surface is modest (~15 methods). It does not violate ISP because consumers use coherent subsets (e.g., WatermarkRepository uses only watermark methods, SectionPersistence uses only section + JSON methods).

**Consequences**:
- Implementors must provide all methods (or raise NotImplementedError for unused operations).
- A future non-S3 backend (unlikely) must implement the full protocol. This is acceptable given the domain specificity.

### ADR-B6-002: RetryOrchestrator at Storage Level, Not Per-Operation

**Context**: We could pass `RetryOrchestrator` to individual methods or let consumers wrap calls in retry logic.

**Decision**: `RetryOrchestrator` is injected at storage construction time and used by all internal S3 operations.

**Rationale**:
- Every S3 operation has the same transient failure modes and should use the same retry strategy.
- Budget coordination requires a single orchestrator instance shared across operations.
- Consumers should not need to think about retry -- the storage layer handles it transparently.

**Consequences**:
- Cannot use different retry strategies for different operation types (e.g., reads vs. writes). If this is needed later, the orchestrator can be made configurable per-operation, but current analysis shows no need.

### ADR-B6-003: Delegate, Then Deprecate (Phased Migration)

**Context**: We could replace all three implementations immediately or migrate gradually.

**Decision**: Four-phase migration with delegation wrappers in Phases 2-3, removal deferred to Phase 4.

**Rationale**:
- Delegation wrappers allow testing the new implementation with the existing test suite unchanged.
- Each phase is independently reversible.
- Phase 4 (removal) can be deferred indefinitely if the wrappers prove stable and the team prefers a conservative approach.

**Consequences**:
- During Phases 2-3, both old and new code coexist. Slight increase in code volume (delegation boilerplate).
- Phase 4 is the only phase that deletes code. It requires a thorough import search.

### ADR-B6-004: Index Operations Accept dict, Not GidLookupIndex

**Context**: The current `DataFramePersistence.save_index()` accepts a `GidLookupIndex` object. The storage protocol could do the same.

**Decision**: Storage protocol accepts `dict[str, Any]` for index operations. Serialization stays with the consumer.

**Rationale**:
- Decouples storage protocol from `services.gid_lookup` module.
- The storage layer's responsibility is bytes-in, bytes-out. Serialization is a consumer concern.
- `GidLookupIndex.serialize()` and `.deserialize()` already exist and work correctly.

**Consequences**:
- Consumers must call `index.serialize()` before `save_index()` and `GidLookupIndex.deserialize()` after `load_index()`. This is a trivial change at each call site.

---

## 19. Success Criteria

### 19.1 Functional

- [ ] `DataFrameStorage` protocol defines all operations from all three current implementations
- [ ] `S3DataFrameStorage` passes all existing tests (via delegation wrappers)
- [ ] All S3 operations route through `RetryOrchestrator`
- [ ] S3 key format is identical to current (backward compatible)
- [ ] Degraded mode uses circuit breaker recovery, not manual timers
- [ ] `S3LocationConfig` is the sole configuration source

### 19.2 Migration

- [ ] `SectionPersistence` delegates S3 I/O to `S3DataFrameStorage` (Phase 2)
- [ ] `DataFramePersistence` delegates all operations to `S3DataFrameStorage` (Phase 3)
- [ ] No consumer code changes required for Phase 1

### 19.3 Quality

- [ ] Unit test coverage for all protocol methods
- [ ] Integration test for roundtrip persistence
- [ ] No new `except Exception` blocks introduced
- [ ] All errors wrapped as `S3TransportError` at the boundary

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD (this document) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unified-dataframe-persistence.md` | Yes |
| DataFramePersistence (analyzed) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/persistence.py` | Yes |
| AsyncS3Client (analyzed) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py` | Yes |
| SectionPersistence (analyzed) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Yes |
| RetryOrchestrator (dependency) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/retry.py` | Yes |
| Exception hierarchy (dependency) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py` | Yes |
| S3LocationConfig (dependency) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Yes |
