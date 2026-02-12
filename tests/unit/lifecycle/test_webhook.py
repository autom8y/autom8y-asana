"""Tests for webhook handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from autom8_asana.lifecycle.webhook import (
    router,
    AsanaWebhookPayload,
    WebhookResponse,
)


@pytest.fixture
def test_app():
    """Create test FastAPI app with webhook router."""
    app = FastAPI()
    app.include_router(router)

    # Mock automation dispatch
    mock_dispatch = MagicMock()
    mock_dispatch.dispatch_async = AsyncMock(return_value={"success": True})
    app.state.automation_dispatch = mock_dispatch

    return app


def test_webhook_payload_validation():
    """Test webhook payload validation."""
    # Valid payload
    payload = AsanaWebhookPayload(
        task_gid="12345",
        task_name="Test Task",
        section_name="CONVERTED",
    )
    assert payload.task_gid == "12345"
    assert payload.section_name == "CONVERTED"

    # Minimal payload
    minimal = AsanaWebhookPayload(task_gid="12345")
    assert minimal.task_gid == "12345"
    assert minimal.section_name is None


def test_webhook_response_model():
    """Test webhook response model."""
    response = WebhookResponse(accepted=True, message="OK")
    assert response.accepted is True
    assert response.message == "OK"


@pytest.mark.asyncio
async def test_handle_asana_webhook_section_change(test_app):
    """Test webhook handler for section change."""
    client = TestClient(test_app)

    # Create payload
    payload = {
        "task_gid": "12345",
        "task_name": "Test Task",
        "section_name": "CONVERTED",
    }

    # Send request
    response = client.post("/api/v1/webhooks/asana", json=payload)

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True


@pytest.mark.asyncio
async def test_handle_asana_webhook_tag_added(test_app):
    """Test webhook handler for tag addition."""
    client = TestClient(test_app)

    # Create payload
    payload = {"task_gid": "12345", "tags": ["route_onboarding"]}

    # Send request
    response = client.post("/api/v1/webhooks/asana", json=payload)

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
