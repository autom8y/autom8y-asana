#!/usr/bin/env python3
"""QA Test for Hotfix 2500444 - Project discovery and schema dispatch."""

import httpx
import time
import sys
import json

# Configuration
AUTH_URL = "https://auth.api.autom8y.io"
ASANA_API_URL = "https://asana.api.autom8y.io"
SERVICE_API_KEY = "sk_prod_Md9G1vsXgHZxBZhEn2YABLjQcvgod5Cn"
SERVICE_NAME = "S2S-demo-service"
TIMEOUT = 60  # seconds


def get_token():
    """Acquire S2S token."""
    print("Acquiring S2S token...")
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{AUTH_URL}/internal/service-token",
            headers={"Content-Type": "application/json", "X-API-Key": SERVICE_API_KEY},
            json={"service_name": SERVICE_NAME},
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        print(f"  Token acquired: {token[:50]}...")
        return token


def test_entity_resolution(token: str, entity_type: str, criteria: dict) -> dict:
    """Test a single entity resolution endpoint."""
    url = f"{ASANA_API_URL}/v1/resolve/{entity_type}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {"criteria": [criteria]}

    print(f"\n{'=' * 60}")
    print(f"Testing: {entity_type.upper()} endpoint")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    print(f"{'=' * 60}")

    start = time.time()
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, headers=headers, json=payload)
            elapsed = time.time() - start

            try:
                response_json = resp.json() if resp.content else {}
            except Exception:
                response_json = {"raw": resp.text[:500] if resp.text else ""}

            result = {
                "entity_type": entity_type,
                "status_code": resp.status_code,
                "elapsed_seconds": round(elapsed, 3),
                "response": response_json,
                "success": resp.status_code == 200,
                "error": None,
            }

            print(f"  Status: {resp.status_code}")
            print(f"  Time: {elapsed:.3f}s")
            print(f"  Response: {json.dumps(result['response'], indent=2)[:500]}")

            # Check for specific error codes
            if resp.status_code == 503:
                error_detail = result["response"].get("detail", {})
                if isinstance(error_detail, dict):
                    result["error"] = error_detail.get("error")
                    print(f"  ERROR: {result['error']}")

    except httpx.TimeoutException:
        elapsed = time.time() - start
        result = {
            "entity_type": entity_type,
            "status_code": None,
            "elapsed_seconds": round(elapsed, 3),
            "response": {},
            "success": False,
            "error": "TIMEOUT",
        }
        print(f"  TIMEOUT after {elapsed:.3f}s!")

    except Exception as e:
        elapsed = time.time() - start
        result = {
            "entity_type": entity_type,
            "status_code": None,
            "elapsed_seconds": round(elapsed, 3),
            "response": {},
            "success": False,
            "error": str(e),
        }
        print(f"  ERROR: {e}")

    return result


def main():
    print("=" * 70)
    print("  QA VALIDATION: Hotfix 2500444")
    print("  Project Discovery & Schema Dispatch")
    print("=" * 70)

    # Get token
    try:
        token = get_token()
    except Exception as e:
        print(f"FATAL: Failed to acquire token: {e}")
        sys.exit(1)

    # Test all 4 entity types with valid E.164 phone numbers
    # Using real phone numbers from S2S demo script for better testing
    test_cases = [
        ("unit", {"phone": "+12604442080", "vertical": "chiropractic"}),
        ("contact", {"contact_phone": "+15551234567"}),
        ("offer", {"offer_id": "OFF-12345"}),  # offer_id is the preferred lookup
        ("business", {"phone": "+12604442080", "vertical": "chiropractic"}),
    ]

    results = []
    for entity_type, criteria in test_cases:
        result = test_entity_resolution(token, entity_type, criteria)
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print(f"\n{'Entity Type':<15} {'Status':<10} {'Time (s)':<12} {'Result':<20}")
    print("-" * 60)

    all_passed = True
    for r in results:
        status = str(r["status_code"]) if r["status_code"] else "N/A"
        time_str = f"{r['elapsed_seconds']:.3f}"
        if r["success"]:
            result_str = "PASS"
        elif r["error"] == "TIMEOUT":
            result_str = "FAIL (TIMEOUT)"
            all_passed = False
        elif r["error"] == "PROJECT_NOT_CONFIGURED":
            result_str = "FAIL (503)"
            all_passed = False
        else:
            result_str = f"FAIL ({r['error'][:15]})" if r["error"] else "FAIL"
            all_passed = False

        print(f"{r['entity_type']:<15} {status:<10} {time_str:<12} {result_str:<20}")

    print("-" * 60)

    # Success Criteria Check
    print("\n" + "=" * 70)
    print("  SUCCESS CRITERIA CHECK")
    print("=" * 70)

    criteria = [
        (
            "All 4 entity types respond (no 503 PROJECT_NOT_CONFIGURED)",
            all(r["error"] != "PROJECT_NOT_CONFIGURED" for r in results),
        ),
        (
            "Contact endpoint responds WITHOUT timeout",
            next((r for r in results if r["entity_type"] == "contact"), {}).get("error")
            != "TIMEOUT",
        ),
        (
            "Response times under 5 seconds",
            all(r["elapsed_seconds"] < 5 for r in results if r["success"]),
        ),
    ]

    print()
    for desc, passed in criteria:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {desc}")

    print("\n" + "=" * 70)
    if all_passed and all(c[1] for c in criteria):
        print("  OVERALL: PASS - Hotfix validation successful")
    else:
        print("  OVERALL: FAIL - Issues detected")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
