#!/usr/bin/env python3
"""Lifecycle Stage Transition

Demonstrates triggering a lifecycle stage change via the webhook API.
Shows how the lifecycle engine orchestrates entity creation, section cascading,
init actions, and dependency wiring when a process transitions stages.

Prerequisites:
    pip install autom8-asana httpx
    export SERVICE_TOKEN="your_service_token"
    export API_BASE_URL="http://localhost:8000"  # or production URL

Related docs:
    - docs/guides/lifecycle-engine.md
"""
import asyncio
import os

import httpx


async def main():
    """Trigger lifecycle stage transitions via webhook API."""
    # Get configuration from environment
    service_token = os.getenv("SERVICE_TOKEN")
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    if not service_token:
        print("Error: SERVICE_TOKEN must be set")
        return

    # Set up API client with service authentication
    headers = {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(base_url=api_base_url, headers=headers, timeout=60.0) as client:
        # Example 1: Trigger CONVERTED transition (Outreach -> Sales)
        print("=" * 60)
        print("Example 1: Convert Outreach to Sales")
        print("=" * 60)

        # Simulate webhook event for a process moving to CONVERTED section
        # In production, this would come from Asana's webhook system
        webhook_event = {
            "events": [
                {
                    "action": "changed",
                    "resource": {
                        "gid": "1234567890123456",  # Process task GID
                        "resource_type": "task"
                    },
                    "change": {
                        "field": "memberships",
                        "action": "added",
                        "new_value": {
                            "section": {
                                "gid": "1234567890123457",  # CONVERTED section GID
                                "name": "CONVERTED"
                            }
                        }
                    }
                }
            ]
        }

        print("Triggering lifecycle transition webhook...")
        print(f"Process GID: {webhook_event['events'][0]['resource']['gid']}")
        print(f"New Section: {webhook_event['events'][0]['change']['new_value']['section']['name']}\n")

        try:
            response = await client.post(
                "/v1/webhooks/lifecycle",
                json=webhook_event
            )

            if response.status_code == 200:
                result = response.json()
                print("Transition completed successfully!\n")

                # Display phase results
                print("Phase 1 - Entity Creation:")
                if result.get("entity_created"):
                    print(f"  Created new Sales process: {result.get('new_entity_gid', 'N/A')}")
                else:
                    print("  No entity created (may be DNC self-loop)")

                print("\nPhase 2 - Configuration:")
                if result.get("cascading_sections"):
                    print("  Updated cascading sections:")
                    for entity_type, section_name in result["cascading_sections"].items():
                        print(f"    - {entity_type}: {section_name}")
                else:
                    print("  No cascading sections updated")

                if result.get("source_completed"):
                    print("  Source process auto-completed: Yes")
                else:
                    print("  Source process auto-completed: No")

                print("\nPhase 3 - Init Actions:")
                if result.get("init_actions"):
                    print(f"  Executed {len(result['init_actions'])} init actions:")
                    for action in result["init_actions"]:
                        status = "SUCCESS" if action.get("success") else "FAILED"
                        print(f"    - {action.get('type', 'unknown')}: {status}")
                else:
                    print("  No init actions configured")

                print("\nPhase 4 - Dependency Wiring:")
                if result.get("dependencies_wired"):
                    print(f"  Wired {result['dependencies_wired']} dependencies")
                else:
                    print("  No dependencies wired")

            elif response.status_code == 400:
                error = response.json()
                print(f"Bad Request: {error.get('detail', 'Unknown error')}")
                if error.get("validation_warnings"):
                    print("\nValidation warnings:")
                    for warning in error["validation_warnings"]:
                        print(f"  - {warning}")

            elif response.status_code == 404:
                print("Process not found or not configured for lifecycle transitions")
                print(response.json())

            elif response.status_code == 503:
                print("Service not ready - registry not initialized")
                print(response.json())

            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return

        except httpx.TimeoutException:
            print("Request timed out. Lifecycle transitions can take 30-60 seconds.")
            print("Check server logs for completion status.")
        except Exception as e:
            print(f"Request failed: {e}")
            raise

        # Example 2: Trigger DID NOT CONVERT transition (Sales -> Outreach)
        print("\n" + "=" * 60)
        print("Example 2: DNC transition (Sales -> Outreach)")
        print("=" * 60)

        # Simulate DNC transition
        dnc_event = {
            "events": [
                {
                    "action": "changed",
                    "resource": {
                        "gid": "1234567890123458",  # Different process GID
                        "resource_type": "task"
                    },
                    "change": {
                        "field": "memberships",
                        "action": "added",
                        "new_value": {
                            "section": {
                                "gid": "1234567890123459",  # DID NOT CONVERT section GID
                                "name": "DID NOT CONVERT"
                            }
                        }
                    }
                }
            ]
        }

        print("Triggering DNC transition webhook...")
        print(f"Process GID: {dnc_event['events'][0]['resource']['gid']}")
        print(f"DNC Routing: Sales -> Outreach (create_new)\n")

        try:
            response = await client.post(
                "/v1/webhooks/lifecycle",
                json=dnc_event
            )

            if response.status_code == 200:
                result = response.json()
                print("DNC transition completed!\n")

                if result.get("dnc_action") == "create_new":
                    print("DNC Action: create_new")
                    print(f"Created new Outreach process: {result.get('new_entity_gid', 'N/A')}")
                elif result.get("dnc_action") == "reopen":
                    print("DNC Action: reopen")
                    print(f"Reopened existing process: {result.get('reopened_gid', 'N/A')}")
                elif result.get("dnc_action") == "deferred":
                    print("DNC Action: deferred (self-loop)")
                    print("No new entity created")
            else:
                print(f"Error: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"Request failed: {e}")

        print("\n" + "=" * 60)
        print("Lifecycle transition examples complete")
        print("=" * 60)
        print("\nNote: These examples use placeholder GIDs. In production:")
        print("  1. Use real process GIDs from your Asana workspace")
        print("  2. Ensure processes are in projects configured in lifecycle_stages.yaml")
        print("  3. Section GIDs must match CONVERTED/DID NOT CONVERT sections")
        print("  4. Webhook events come from Asana, not manual POST requests")


if __name__ == "__main__":
    asyncio.run(main())
