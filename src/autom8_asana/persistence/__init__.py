"""Save Orchestration Layer for autom8_asana SDK.

Provides Unit of Work pattern for batched Asana API operations.

The Save Orchestration Layer enables Django-ORM-style deferred saves
where multiple model changes are collected and executed in optimized
batches rather than immediately persisting each change.

Main API:
    SaveSession: Context manager for batched save operations

Data Models:
    EntityState: Entity lifecycle state (NEW, CLEAN, MODIFIED, DELETED)
    OperationType: API operation type (CREATE, UPDATE, DELETE)
    PlannedOperation: Preview of a planned operation
    SaveError: Error information for a failed operation
    SaveResult: Result of a commit operation

Exceptions:
    SaveOrchestrationError: Base exception for save errors
    SessionClosedError: Operation on closed session
    CyclicDependencyError: Dependency cycle detected
    DependencyResolutionError: Dependency resolution failed
    PartialSaveError: Some operations failed

Example - Basic Usage:
    async with SaveSession(client) as session:
        # Track entities for changes
        session.track(task1)
        session.track(task2)

        # Modify tracked entities
        task1.name = "Updated Name"
        task2.completed = True

        # Commit all changes in optimized batches
        result = await session.commit_async()

        if result.success:
            print("All saved!")
        else:
            for error in result.failed:
                print(f"Failed: {error.entity.gid}")

Example - New Entities with Dependencies:
    async with SaveSession(client) as session:
        # Create parent task
        parent = Task(gid="temp_parent", name="Parent Task")
        session.track(parent)

        # Create child with parent reference
        child = Task(
            gid="temp_child",
            name="Child Task",
            parent=NameGid(gid="temp_parent"),
        )
        session.track(child)

        # Commit - parent saved first, child gets resolved GID
        result = await session.commit_async()
        print(f"Parent GID: {parent.gid}")  # Real GID from API
        print(f"Child GID: {child.gid}")    # Real GID from API

Example - Sync Usage:
    with SaveSession(client) as session:
        session.track(task)
        task.name = "Updated"
        result = session.commit()

Example - With Hooks:
    async with SaveSession(client) as session:
        @session.on_pre_save
        def validate(entity, op):
            if op == OperationType.CREATE and not entity.name:
                raise ValueError("Name required")

        @session.on_post_save
        async def notify(entity, op, data):
            await send_notification(entity.gid)

        session.track(task)
        await session.commit_async()
"""

from autom8_asana.persistence.cascade import (
    CascadeExecutor,
    CascadeOperation,
    CascadeResult,
    cascade_field,
)
from autom8_asana.persistence.exceptions import (
    CyclicDependencyError,
    DependencyResolutionError,
    # TDD-HARDENING-A: Exception hierarchy cleanup (FR-EXC-003, FR-EXC-004)
    GidValidationError,
    PartialSaveError,
    PositioningConflictError,
    SaveOrchestrationError,
    # TDD-TRIAGE-FIXES: P1 method error propagation
    SaveSessionError,
    SessionClosedError,
    # TDD-0011: Unsupported operation
    UnsupportedOperationError,
    ValidationError,  # Deprecated alias for backward compatibility
)
from autom8_asana.persistence.healing import HealingManager
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
    # TDD-0011: Action types
    ActionType,
    EntityState,
    HealingReport,
    # TDD-DETECTION/ADR-0095: Self-healing models
    HealingResult,
    OperationType,
    PlannedOperation,
    SaveError,
    SaveResult,
)
from autom8_asana.persistence.session import SaveSession

__all__ = [
    # Main API
    "SaveSession",
    # Data models
    "EntityState",
    "OperationType",
    "PlannedOperation",
    "SaveError",
    "SaveResult",
    # Action models (TDD-0011)
    "ActionType",
    "ActionOperation",
    "ActionResult",
    # Self-healing models (TDD-DETECTION/ADR-0095, TDD-TECH-DEBT-REMEDIATION)
    "HealingResult",
    "HealingReport",
    "HealingManager",
    # Cascade models (Phase 3)
    "CascadeOperation",
    "CascadeResult",
    "CascadeExecutor",
    "cascade_field",
    # Exceptions
    "SaveOrchestrationError",
    "SessionClosedError",
    "CyclicDependencyError",
    "DependencyResolutionError",
    "PartialSaveError",
    "UnsupportedOperationError",
    "SaveSessionError",
    # TDD-HARDENING-A: Exception hierarchy cleanup (FR-EXC-003, FR-EXC-004)
    "GidValidationError",
    "PositioningConflictError",
    "ValidationError",  # Deprecated alias for backward compatibility
]
