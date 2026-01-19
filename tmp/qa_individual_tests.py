#!/usr/bin/env python3
"""Individual endpoint tests with verbose output."""

import httpx
import time
import sys
import json

# Configuration
AUTH_URL = "https://auth.api.autom8y.io"
ASANA_API_URL = "https://asana.api.autom8y.io"
SERVICE_API_KEY = "sk_prod_Md9G1vsXgHZxBZhEn2YABLjQcvgod5Cn"
SERVICE_NAME = "S2S-demo-service"


def get_token():
    """Acquire S2S token."""
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{AUTH_URL}/internal/service-token",
            headers={"Content-Type": "application/json", "X-API-Key": SERVICE_API_KEY},
            json={"service_name": SERVICE_NAME},
        )
        resp.raise_for_status()
        return resp.json().get("access_token")


def test_endpoint(token: str, entity_type: str, criteria: dict, timeout: int = 60):
    """Test a single endpoint with full diagnostic output."""
    url = f"{ASANA_API_URL}/v1/resolve/{entity_type}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {"criteria": [criteria]}

    print(f"\n{'=' * 70}")
    print(f"  TESTING: {entity_type.upper()}")
    print(f"{'=' * 70}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    print(f"Timeout: {timeout}s")
    print("-" * 70)

    start = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            elapsed = time.time() - start

            print(f"Status Code: {resp.status_code}")
            print(f"Elapsed: {elapsed:.3f}s")
            print(f"Headers: {dict(resp.headers)}")
            print(f"Raw Response: {resp.text[:1000]}")

            if resp.status_code == 200:
                print("\n>>> SUCCESS <<<")
                return True
            elif resp.status_code == 503:
                print("\n>>> FAIL: 503 Service Unavailable <<<")
                return False
            else:
                print(f"\n>>> Unexpected status: {resp.status_code} <<<")
                return False

    except httpx.TimeoutException:
        elapsed = time.time() - start
        print(f"\n>>> TIMEOUT after {elapsed:.3f}s <<<")
        return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n>>> ERROR after {elapsed:.3f}s: {e} <<<")
        return False


def main():
    print("=" * 70)
    print("  INDIVIDUAL ENDPOINT TESTS - Hotfix 2500444")
    print("=" * 70)

    token = get_token()
    print(f"Token acquired: {token[:50]}...")

    results = {}

    # Test 1: Unit (should work)
    results["unit"] = test_endpoint(
        token, "unit", {"phone": "+12604442080", "vertical": "chiropractic"}, timeout=30
    )

    # Test 2: Business (should work)
    results["business"] = test_endpoint(
        token,
        "business",
        {"phone": "+12604442080", "vertical": "chiropractic"},
        timeout=30,
    )

    # Test 3: Offer (testing with offer_id)
    results["offer"] = test_endpoint(
        token, "offer", {"offer_id": "OFF-12345"}, timeout=30
    )

    # Test 4: Contact (was timing out - critical test)
    print("\n" + "!" * 70)
    print("  CRITICAL TEST: Contact endpoint (was timing out before hotfix)")
    print("!" * 70)
    results["contact"] = test_endpoint(
        token,
        "contact",
        {"contact_phone": "+15551234567"},
        timeout=90,  # Give extra time to see if it completes
    )

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for entity, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {entity}: {status}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
