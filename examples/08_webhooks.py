"""Example: Webhook Setup and Verification

Demonstrates:
- Creating webhooks for resources (projects, tasks)
- Verifying webhook signatures (HMAC-SHA256)
- Handling webhook handshake events
- Example webhook event handler
- Listing and deleting webhooks

Requirements:
- ASANA_PAT environment variable set
- Valid project GID (provide via --project arg)
- Publicly accessible webhook target URL (provide via --target arg)

Usage:
    export ASANA_PAT="your_token_here"
    python examples/08_webhooks.py --project PROJECT_GID --target https://your-server.com/webhook

Output:
    Webhook creation and signature verification examples

Note:
    This example shows the SDK API. To receive actual webhook events,
    you need a running web server at the target URL that responds to
    the handshake and processes events.
"""

import asyncio
import json
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from autom8_asana.clients.webhooks import WebhooksClient
from _config import get_project_gid, get_config_instructions


def demonstrate_signature_verification() -> None:
    """Show how to verify webhook signatures.

    This would be used in your webhook handler endpoint to verify
    that incoming requests are genuinely from Asana.
    """
    print("\n=== Webhook Signature Verification ===")

    # Example webhook event body (what Asana sends)
    event_body = b'{"events":[{"action":"changed","resource":{"gid":"123"}}]}'

    # The secret you received during webhook handshake
    webhook_secret = "your_webhook_secret_from_handshake"

    # The signature from X-Hook-Signature header
    # (In production, this comes from the HTTP request header)
    signature = "computed_signature_from_asana"

    # Verify the signature
    is_valid = WebhooksClient.verify_signature(
        request_body=event_body,
        signature=signature,
        secret=webhook_secret,
    )

    print(f"Signature verification example:")
    print(f"  Valid: {is_valid}")
    print("\nIn production, reject requests with invalid signatures:")
    print("  if not WebhooksClient.verify_signature(...):")
    print("      return 401 Unauthorized")


def example_webhook_handler() -> None:
    """Example webhook handler function.

    This shows the structure of a webhook event handler that would
    run in your web server (Flask, FastAPI, etc.).
    """
    print("\n=== Example Webhook Handler ===")

    example_code = '''
# Example Flask webhook handler
from flask import Flask, request, jsonify
from autom8_asana.clients.webhooks import WebhooksClient

app = Flask(__name__)
WEBHOOK_SECRET = "your_secret"  # Store securely

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    # 1. Verify signature
    signature = request.headers.get("X-Hook-Signature", "")
    if not WebhooksClient.verify_signature(
        request_body=request.get_data(),
        signature=signature,
        secret=WEBHOOK_SECRET,
    ):
        return jsonify({"error": "Invalid signature"}), 401

    # 2. Handle handshake event
    event_data = request.get_json()
    if "X-Hook-Secret" in request.headers:
        # This is the handshake - save the secret
        secret = request.headers["X-Hook-Secret"]
        # Store secret securely for future verification
        # Return 200 to confirm handshake
        return jsonify({}), 200

    # 3. Process events
    events = event_data.get("events", [])
    for event in events:
        action = event.get("action")  # changed, added, removed, deleted, undeleted
        resource = event.get("resource")  # {gid, resource_type}
        parent = event.get("parent")  # Parent resource if applicable

        # Your business logic here
        print(f"Event: {action} on {resource['resource_type']} {resource['gid']}")

    return jsonify({}), 200
'''

    print(example_code)


async def create_webhook(
    client: AsanaClient, resource_gid: str, target_url: str
) -> str:
    """Create a webhook for a resource.

    Args:
        client: AsanaClient instance
        resource_gid: GID of resource to watch (project, task, etc.)
        target_url: Your webhook endpoint URL

    Returns:
        Created webhook GID
    """
    print("\n=== Creating Webhook ===")

    # Create webhook
    # Note: The target URL must respond to the handshake within 72 hours
    webhook = await client.webhooks.create_async(
        resource=resource_gid,
        target=target_url,
    )

    print(f"Created webhook: {webhook.gid}")
    print(f"  Resource: {webhook.resource.gid if webhook.resource else 'N/A'}")
    print(f"  Target: {webhook.target}")
    print(f"  Active: {webhook.active}")

    print("\nIMPORTANT: Webhook handshake:")
    print(f"  1. Asana will POST to {target_url}")
    print("  2. Request will include X-Hook-Secret header")
    print("  3. Your server must respond with 200 OK")
    print("  4. Save the X-Hook-Secret for signature verification")
    print("  5. Webhook becomes active after successful handshake")

    return webhook.gid


async def list_webhooks(client: AsanaClient, workspace_gid: str) -> None:
    """List all webhooks in a workspace."""
    print("\n=== Listing Webhooks ===")

    # List webhooks for workspace
    webhooks = await client.webhooks.list_async(workspace=workspace_gid).take(10)

    if webhooks:
        print(f"Found {len(webhooks)} webhooks:")
        for webhook in webhooks:
            print(f"  - {webhook.gid}")
            print(f"    Resource: {webhook.resource.gid if webhook.resource else 'N/A'}")
            print(f"    Target: {webhook.target}")
            print(f"    Active: {webhook.active}")
    else:
        print("  No webhooks found")


async def delete_webhook(client: AsanaClient, webhook_gid: str) -> None:
    """Delete a webhook."""
    print(f"\n=== Deleting Webhook ===")

    await client.webhooks.delete_async(webhook_gid)
    print(f"Deleted webhook: {webhook_gid}")


async def demonstrate_event_types() -> None:
    """Show the different event types Asana sends."""
    print("\n=== Webhook Event Types ===")

    event_types = {
        "changed": "Resource was modified",
        "added": "Resource was added to parent",
        "removed": "Resource was removed from parent",
        "deleted": "Resource was deleted",
        "undeleted": "Resource was restored from trash",
    }

    print("Asana sends these event types:")
    for event_type, description in event_types.items():
        print(f"  {event_type:12} - {description}")

    print("\nExample event payload:")
    example_event = {
        "events": [
            {
                "action": "changed",
                "created_at": "2024-01-15T10:30:00.000Z",
                "parent": None,
                "resource": {
                    "gid": "123456789",
                    "resource_type": "task",
                },
                "type": "task",
                "user": {
                    "gid": "987654321",
                    "resource_type": "user",
                },
            }
        ]
    }

    print(json.dumps(example_event, indent=2))


async def main(project_gid: str, target_url: str | None) -> None:
    """Run all webhook examples."""
    print("autom8_asana SDK - Webhooks Examples")

    # Show signature verification (doesn't need API)
    demonstrate_signature_verification()

    # Show example handler code
    example_webhook_handler()

    # Show event types
    await demonstrate_event_types()

    if target_url:
        async with AsanaClient() as client:
            # Create webhook
            webhook_gid = await create_webhook(client, project_gid, target_url)

            # Note: You would typically keep the webhook active
            # For this demo, we'll delete it immediately
            print("\n(Normally you would keep the webhook active)")
            print("(For this demo, we'll delete it to avoid orphaned webhooks)")

            # Delete the webhook
            await delete_webhook(client, webhook_gid)
    else:
        print("\n=== Skipping webhook creation (no --target provided) ===")
        print("To create a webhook, provide a public URL:")
        print("  python 08_webhooks.py --project GID --target https://your-server.com/webhook")

    print("\n=== Complete ===")
    print("Key Takeaways:")
    print("  - Webhooks notify your app of Asana changes in real-time")
    print("  - Always verify signatures using WebhooksClient.verify_signature()")
    print("  - Handle the handshake event (X-Hook-Secret header)")
    print("  - Process events: changed, added, removed, deleted, undeleted")
    print("  - Target URL must be publicly accessible and return 200 OK")


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate webhook setup and verification")
    parser.add_argument(
        "--project",
        default=get_project_gid(),
        help="Project GID to watch (or set ASANA_PROJECT_GID env var)",
    )
    parser.add_argument(
        "--target",
        help="Webhook target URL (must be publicly accessible)",
    )
    args = parser.parse_args()

    if not args.project:
        print("ERROR: No project GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.project, args.target))
