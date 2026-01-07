"""Asana-specific response handling for autom8y-http integration.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-004: Handles Asana-specific response unwrapping
and error parsing, translating HTTP responses into domain exceptions.

The Asana API wraps all responses in a {"data": ...} envelope. This module
extracts the actual data and converts error responses to appropriate exceptions.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from autom8_asana.exceptions import (
    AsanaError,
    RateLimitError,
)

__all__ = ["AsanaResponseHandler"]


class AsanaResponseHandler:
    """Handles Asana-specific response processing.

    Per TDD-ASANA-HTTP-MIGRATION-001/FR-004: Provides response unwrapping
    and error translation for Asana API responses.

    The Asana API returns all successful responses wrapped in a {"data": ...}
    envelope. Error responses include an "errors" array with detailed messages.

    This class provides static methods for:
    - Unwrapping successful responses
    - Extracting pagination information
    - Parsing error responses into domain exceptions

    Example:
        >>> response = await http_client.get("/tasks/123")
        >>> task = AsanaResponseHandler.unwrap_response(response)
        >>> print(task["gid"])

        >>> # Paginated response
        >>> data, next_offset = AsanaResponseHandler.unwrap_paginated_response(response)
    """

    @staticmethod
    def unwrap_response(response: httpx.Response) -> dict[str, Any]:
        """Unwrap Asana response envelope.

        Asana wraps all responses in {"data": ...}. This method:
        1. Checks for error status codes
        2. Parses JSON
        3. Extracts "data" key
        4. Returns data or raises error

        Args:
            response: httpx Response object.

        Returns:
            Unwrapped response data (without {"data": ...} envelope).
            If the response doesn't contain a "data" key, returns the
            entire JSON body.

        Raises:
            AsanaError: If JSON parsing fails.
            RateLimitError: If 429 response.
            ServerError: If 5xx response.
            Other AsanaError subclasses: Based on status code.
        """
        if response.status_code >= 400:
            raise AsanaResponseHandler.parse_error(response)

        try:
            result = response.json()
        except json.JSONDecodeError as e:
            request_id = response.headers.get("X-Request-Id", "unknown")
            body_snippet = response.text[:200] if response.text else "(empty)"
            raise AsanaError(
                f"Invalid JSON response (HTTP {response.status_code}, "
                f"request_id={request_id}): {e}. Body: {body_snippet}"
            ) from e

        if isinstance(result, dict) and "data" in result:
            return result["data"]  # type: ignore[no-any-return]
        return result  # type: ignore[no-any-return]

    @staticmethod
    def unwrap_paginated_response(
        response: httpx.Response,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Unwrap paginated Asana response.

        Asana pagination returns:
        {
            "data": [...],
            "next_page": {
                "offset": "xxx",
                "path": "/...",
                "uri": "https://..."
            }
        }

        Args:
            response: httpx Response object.

        Returns:
            Tuple of (data list, next_offset or None).
            - data: List of resource dictionaries
            - next_offset: Pagination offset for next page, or None if last page

        Raises:
            AsanaError: If JSON parsing fails.
            RateLimitError: If 429 response.
            ServerError: If 5xx response.
        """
        if response.status_code >= 400:
            raise AsanaResponseHandler.parse_error(response)

        try:
            result = response.json()
        except json.JSONDecodeError as e:
            request_id = response.headers.get("X-Request-Id", "unknown")
            raise AsanaError(
                f"Invalid JSON response (HTTP {response.status_code}, "
                f"request_id={request_id}): {e}"
            ) from e

        data: list[dict[str, Any]] = []
        next_offset: str | None = None

        if isinstance(result, dict):
            data = result.get("data", [])
            next_page = result.get("next_page")
            if next_page and isinstance(next_page, dict):
                next_offset = next_page.get("offset")

        return data, next_offset

    @staticmethod
    def parse_error(response: httpx.Response) -> AsanaError:
        """Parse error response into domain exception.

        Parses the response body and returns the most specific exception
        subclass based on status code. Includes debugging context:
        HTTP status, request ID, and body snippet.

        Asana error responses follow the format:
        {
            "errors": [
                {"message": "...", "help": "...", "phrase": "..."}
            ]
        }

        Args:
            response: httpx Response object with error status code.

        Returns:
            Appropriate AsanaError subclass based on status code:
            - 429: RateLimitError with retry_after from headers
            - 5xx: ServerError
            - 4xx: Specific error type from AsanaError.from_response
        """
        status_code = response.status_code

        # Special handling for rate limit (429)
        if status_code == 429:
            return AsanaResponseHandler._parse_rate_limit_error(response)

        # Use the standard AsanaError.from_response for other errors
        # This preserves all the existing error mapping logic
        return AsanaError.from_response(response)

    @staticmethod
    def _parse_rate_limit_error(response: httpx.Response) -> RateLimitError:
        """Parse rate limit (429) error with Retry-After header.

        Args:
            response: httpx Response object with 429 status.

        Returns:
            RateLimitError with retry_after from Retry-After header.
        """
        # Parse retry_after from header
        retry_after: int | None = None
        if "Retry-After" in response.headers:
            try:
                retry_after = int(response.headers["Retry-After"])
            except ValueError:
                pass

        # Get message from response body
        request_id = response.headers.get("X-Request-Id")
        context = "HTTP 429"
        if request_id:
            context += f", request_id={request_id}"

        message = f"Rate limit exceeded ({context})"

        try:
            body = response.json()
            if "errors" in body and isinstance(body["errors"], list):
                errors = body["errors"]
                if errors:
                    messages = [e.get("message", "Unknown error") for e in errors]
                    message = f"{'; '.join(messages)} ({context})"
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            pass

        return RateLimitError(
            message,
            status_code=429,
            response=response,
            retry_after=retry_after,
        )
