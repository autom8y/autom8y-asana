"""Batch API models.

Immutable dataclasses for batch request/response handling.
Per TDD-0005: Batch API for Bulk Operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autom8_asana.exceptions import AsanaError


@dataclass(frozen=True)
class BatchRequest:
    """Single request within a batch operation.

    Represents one action to be executed in an Asana batch request.
    Immutable to ensure batch contents can't change during execution.

    Attributes:
        relative_path: API path relative to base URL (e.g., "/tasks", "/tasks/123")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body for POST/PUT operations
        options: Query parameters (e.g., opt_fields)

    Example:
        # Create a task
        BatchRequest(
            relative_path="/tasks",
            method="POST",
            data={"name": "New Task", "projects": ["12345"]},
        )

        # Update a task
        BatchRequest(
            relative_path="/tasks/67890",
            method="PUT",
            data={"completed": True},
        )

        # Get a task with specific fields
        BatchRequest(
            relative_path="/tasks/67890",
            method="GET",
            options={"opt_fields": "name,completed,assignee"},
        )
    """

    relative_path: str
    method: str
    data: dict[str, Any] | None = None
    options: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate request configuration."""
        valid_methods = {"GET", "POST", "PUT", "DELETE"}
        if self.method.upper() not in valid_methods:
            raise ValueError(
                f"method must be one of {valid_methods}, got '{self.method}'"
            )
        if not self.relative_path.startswith("/"):
            raise ValueError(
                f"relative_path must start with '/', got '{self.relative_path}'"
            )

    def to_action_dict(self) -> dict[str, Any]:
        """Convert to Asana batch action format.

        Returns:
            Dict matching Asana's batch action schema:
            {
                "relative_path": "/tasks",
                "method": "POST",
                "data": {...},      # optional
                "options": {...}    # optional
            }
        """
        action: dict[str, Any] = {
            "relative_path": self.relative_path,
            "method": self.method.upper(),
        }
        if self.data is not None:
            action["data"] = self.data
        if self.options is not None:
            action["options"] = self.options
        return action


@dataclass(frozen=True)
class BatchResult:
    """Result of a single action within a batch operation.

    Each BatchResult corresponds to one BatchRequest, preserving order.
    Check the `success` property to determine if the action succeeded.

    Attributes:
        status_code: HTTP status code returned for this action
        body: Response body (parsed JSON) or None
        headers: Response headers dict or None
        request_index: Original index of the request in the batch (for correlation)

    Example:
        results = await client.batch.execute_async(requests)

        for i, result in enumerate(results):
            if result.success:
                print(f"Action {i} succeeded: {result.data}")
            else:
                print(f"Action {i} failed: {result.error}")
    """

    status_code: int
    body: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    request_index: int = 0

    @property
    def success(self) -> bool:
        """Whether the action succeeded (2xx status code)."""
        return 200 <= self.status_code < 300

    @property
    def error(self) -> AsanaError | None:
        """Extract error information if action failed.

        Returns:
            AsanaError with details if failed, None if succeeded.
        """
        if self.success:
            return None

        message = "Batch action failed"
        errors: list[dict[str, Any]] = []

        if self.body and isinstance(self.body, dict) and "errors" in self.body:
            errors = self.body.get("errors", [])
            messages = [e.get("message", "Unknown error") for e in errors]
            message = "; ".join(messages) if messages else message

        return AsanaError(
            message,
            status_code=self.status_code,
            errors=errors,
        )

    @property
    def data(self) -> dict[str, Any] | None:
        """Extract the 'data' field from successful responses.

        Asana wraps responses in {"data": ...}. This property
        unwraps for convenience.

        Returns:
            The unwrapped data dict, or None if not present/failed.
        """
        if not self.success or not self.body:
            return None
        if isinstance(self.body, dict) and "data" in self.body:
            data_value = self.body["data"]
            if isinstance(data_value, dict):
                return data_value
            return None
        # If no "data" wrapper, return body as-is if it's a dict
        if isinstance(self.body, dict):
            return self.body
        return None

    @classmethod
    def from_asana_response(
        cls,
        response_item: dict[str, Any],
        request_index: int,
    ) -> BatchResult:
        """Create BatchResult from Asana batch response item.

        Args:
            response_item: Single item from Asana batch response array
            request_index: Original index for correlation

        Returns:
            BatchResult instance
        """
        return cls(
            status_code=response_item.get("status_code", 500),
            body=response_item.get("body"),
            headers=response_item.get("headers"),
            request_index=request_index,
        )


@dataclass
class BatchSummary:
    """Summary statistics for a batch operation.

    Provides convenient access to aggregate information about
    batch execution results.

    Attributes:
        results: All BatchResult objects in original order
    """

    results: list[BatchResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of actions."""
        return len(self.results)

    @property
    def succeeded(self) -> int:
        """Number of successful actions."""
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        """Number of failed actions."""
        return sum(1 for r in self.results if not r.success)

    @property
    def all_succeeded(self) -> bool:
        """Whether all actions succeeded."""
        return all(r.success for r in self.results)

    @property
    def successful_results(self) -> list[BatchResult]:
        """Filter to only successful results."""
        return [r for r in self.results if r.success]

    @property
    def failed_results(self) -> list[BatchResult]:
        """Filter to only failed results."""
        return [r for r in self.results if not r.success]
