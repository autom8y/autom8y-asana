#!/usr/bin/env python3
"""Webhook event handler for Asana task updates.

This example demonstrates:
- Building a minimal FastAPI webhook receiver
- Validating webhook authentication tokens
- Parsing Asana task payloads
- Processing task updates in the background
- Cache invalidation on task changes
- Error handling and logging

The webhook endpoint accepts POST requests from Asana Rules actions
that send full task JSON payloads. It validates the request, enqueues
background processing, and returns 200 immediately.

Webhook flow:
1. Asana Rule triggers on task change
2. Rule action POSTs task JSON to /api/v1/webhooks/inbound?token=<secret>
3. Endpoint validates token, parses payload
4. Background task invalidates stale cache entries
5. Background task dispatches to event handlers

Usage:
    export WEBHOOK_TOKEN="your_webhook_secret"
    export API_BASE_URL="http://localhost:8000"
    .venv/bin/python docs/examples/10-webhook-handler.py

    Then trigger a webhook by updating a task in Asana (if Rules are configured)

Prerequisites:
- Python 3.10+
- fastapi, httpx, uvicorn installed
- Webhook configured in Asana Rules
- Shared secret token configured

Related docs:
    - src/autom8_asana/api/routes/webhooks.py
    - docs/design/TDD-GAP-02-webhook-inbound.md
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone


async def send_test_webhook(
    base_url: str,
    webhook_token: str,
    task_payload: dict,
) -> dict:
    """Send a test webhook request to the API.

    This simulates an Asana Rule action posting a task update.

    Args:
        base_url: API base URL (e.g., "http://localhost:8000")
        webhook_token: Webhook authentication token
        task_payload: Task JSON payload to send

    Returns:
        Response dict from webhook endpoint
    """
    import httpx

    url = f"{base_url}/api/v1/webhooks/inbound"
    params = {"token": webhook_token}
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            params=params,
            headers=headers,
            json=task_payload,
        )
        response.raise_for_status()
        return response.json()


def create_example_task_payload(
    gid: str = "1234567890123456",
    name: str = "Example Task",
    completed: bool = False,
) -> dict:
    """Create an example task payload for testing.

    This mimics the structure sent by Asana Rules actions.

    Args:
        gid: Task GID
        name: Task name
        completed: Completion status

    Returns:
        Task payload dict
    """
    # Generate realistic timestamp
    modified_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "gid": gid,
        "resource_type": "task",
        "name": name,
        "completed": completed,
        "modified_at": modified_at,
        "created_at": "2024-01-01T00:00:00.000Z",
        "assignee": {
            "gid": "9876543210987654",
            "name": "John Doe",
        },
        "notes": "Example task notes",
        "due_on": "2024-12-31",
        "custom_fields": [
            {
                "gid": "1111111111111111",
                "name": "Status",
                "resource_subtype": "enum",
                "display_value": "In Progress",
                "enum_value": {
                    "gid": "2222222222222222",
                    "name": "In Progress",
                },
            },
            {
                "gid": "3333333333333333",
                "name": "Priority",
                "resource_subtype": "enum",
                "display_value": "High",
                "enum_value": {
                    "gid": "4444444444444444",
                    "name": "High",
                },
            },
        ],
        "memberships": [
            {
                "project": {
                    "gid": "5555555555555555",
                    "name": "Example Project",
                },
                "section": {
                    "gid": "6666666666666666",
                    "name": "In Progress",
                },
            }
        ],
    }


async def test_webhook_authentication(
    base_url: str,
    webhook_token: str,
) -> None:
    """Test webhook authentication mechanisms.

    Demonstrates:
    - Valid token authentication
    - Missing token rejection
    - Invalid token rejection

    Args:
        base_url: API base URL
        webhook_token: Valid webhook authentication token
    """
    import httpx

    url = f"{base_url}/api/v1/webhooks/inbound"
    headers = {"Content-Type": "application/json"}
    task_payload = create_example_task_payload()

    print("Testing webhook authentication...")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Valid token
        print("Test 1: Valid token")
        try:
            response = await client.post(
                url,
                params={"token": webhook_token},
                headers=headers,
                json=task_payload,
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except Exception as exc:
            print(f"  Error: {exc}")

        print()

        # Test 2: Missing token
        print("Test 2: Missing token")
        try:
            response = await client.post(
                url,
                headers=headers,
                json=task_payload,
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except httpx.HTTPStatusError as exc:
            print(f"  Status: {exc.response.status_code}")
            print(f"  Error: {exc.response.json()}")

        print()

        # Test 3: Invalid token
        print("Test 3: Invalid token")
        try:
            response = await client.post(
                url,
                params={"token": "invalid_token_12345"},
                headers=headers,
                json=task_payload,
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except httpx.HTTPStatusError as exc:
            print(f"  Status: {exc.response.status_code}")
            print(f"  Error: {exc.response.json()}")

        print()


async def test_webhook_payload_validation(
    base_url: str,
    webhook_token: str,
) -> None:
    """Test webhook payload validation.

    Demonstrates:
    - Valid task payload acceptance
    - Empty payload handling
    - Missing GID rejection
    - Invalid JSON rejection

    Args:
        base_url: API base URL
        webhook_token: Valid webhook authentication token
    """
    import httpx

    url = f"{base_url}/api/v1/webhooks/inbound"
    params = {"token": webhook_token}
    headers = {"Content-Type": "application/json"}

    print("Testing webhook payload validation...")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Valid payload
        print("Test 1: Valid task payload")
        valid_payload = create_example_task_payload()
        try:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                json=valid_payload,
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except Exception as exc:
            print(f"  Error: {exc}")

        print()

        # Test 2: Empty payload
        print("Test 2: Empty payload")
        try:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                json={},
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except Exception as exc:
            print(f"  Error: {exc}")

        print()

        # Test 3: Missing GID
        print("Test 3: Missing GID")
        missing_gid_payload = {"name": "Task without GID", "completed": False}
        try:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                json=missing_gid_payload,
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except httpx.HTTPStatusError as exc:
            print(f"  Status: {exc.response.status_code}")
            print(f"  Error: {exc.response.json()}")

        print()

        # Test 4: Invalid JSON
        print("Test 4: Invalid JSON")
        try:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                content="not valid json",
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except httpx.HTTPStatusError as exc:
            print(f"  Status: {exc.response.status_code}")
            print(f"  Error: {exc.response.json()}")

        print()


async def simulate_webhook_events(
    base_url: str,
    webhook_token: str,
    num_events: int = 5,
) -> None:
    """Simulate a sequence of webhook events.

    This demonstrates how multiple task updates would be processed
    in a real scenario.

    Args:
        base_url: API base URL
        webhook_token: Valid webhook authentication token
        num_events: Number of events to simulate
    """
    print(f"Simulating {num_events} webhook events...")
    print("=" * 60)

    for i in range(1, num_events + 1):
        # Create varying task payloads
        task_payload = create_example_task_payload(
            gid=f"1234567890{i:06d}",
            name=f"Task {i}",
            completed=(i % 3 == 0),  # Every 3rd task is completed
        )

        print(f"\nEvent {i}: Sending task update for {task_payload['name']}")
        print(f"  GID: {task_payload['gid']}")
        print(f"  Completed: {task_payload['completed']}")
        print(f"  Modified: {task_payload['modified_at']}")

        try:
            response = await send_test_webhook(
                base_url=base_url,
                webhook_token=webhook_token,
                task_payload=task_payload,
            )
            print(f"  Response: {response['status']}")

        except Exception as exc:
            print(f"  Error: {exc}")

        # Small delay between events
        await asyncio.sleep(0.5)

    print("\nAll events sent!")
    print("Note: Events are processed in background - check server logs")


async def main() -> None:
    """Demonstrate webhook handling capabilities."""

    # Get configuration from environment
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    webhook_token = os.getenv("WEBHOOK_TOKEN")

    if not webhook_token:
        print("ERROR: WEBHOOK_TOKEN environment variable not set")
        print("Set it with: export WEBHOOK_TOKEN=your_webhook_secret")
        print()
        print("In production, this token should match the value configured in:")
        print("  - WEBHOOK_INBOUND_TOKEN environment variable")
        print("  - Asana Rule action URL: ?token=<same_value>")
        sys.exit(1)

    print(f"API Base URL: {base_url}")
    print(f"Webhook Token: {'*' * (len(webhook_token) - 4)}{webhook_token[-4:]}")
    print()

    try:
        # Example 1: Test authentication
        await test_webhook_authentication(
            base_url=base_url,
            webhook_token=webhook_token,
        )

        print()

        # Example 2: Test payload validation
        await test_webhook_payload_validation(
            base_url=base_url,
            webhook_token=webhook_token,
        )

        print()

        # Example 3: Simulate webhook events
        await simulate_webhook_events(
            base_url=base_url,
            webhook_token=webhook_token,
            num_events=5,
        )

        print()
        print("=" * 60)
        print("Webhook examples complete!")
        print()
        print("Integration checklist:")
        print("  [ ] Configure WEBHOOK_INBOUND_TOKEN in server environment")
        print("  [ ] Create Asana Rule to POST to /api/v1/webhooks/inbound")
        print("  [ ] Add ?token=<secret> query parameter to Rule URL")
        print("  [ ] Test with actual task updates in Asana")
        print("  [ ] Monitor server logs for background processing")
        print("  [ ] Verify cache invalidation in structured logs")

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
