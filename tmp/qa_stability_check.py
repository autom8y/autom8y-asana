#!/usr/bin/env python3
"""Check API stability - multiple requests to see if 503 is intermittent."""

import httpx
import time
import json

AUTH_URL = "https://auth.api.autom8y.io"
ASANA_API_URL = "https://asana.api.autom8y.io"
SERVICE_API_KEY = "sk_prod_Md9G1vsXgHZxBZhEn2YABLjQcvgod5Cn"
SERVICE_NAME = "S2S-demo-service"


def get_token():
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{AUTH_URL}/internal/service-token",
            headers={"Content-Type": "application/json", "X-API-Key": SERVICE_API_KEY},
            json={"service_name": SERVICE_NAME},
        )
        resp.raise_for_status()
        return resp.json().get("access_token")


def main():
    print("=" * 70)
    print("  API STABILITY CHECK")
    print("=" * 70)

    token = get_token()
    print("Token acquired.\n")

    endpoints = [
        ("unit", {"phone": "+12604442080", "vertical": "chiropractic"}),
        ("contact", {"contact_phone": "+15551234567"}),
        ("offer", {"offer_id": "OFF-12345"}),
        ("business", {"phone": "+12604442080", "vertical": "chiropractic"}),
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Test each endpoint 3 times with delays
    for entity, criteria in endpoints:
        url = f"{ASANA_API_URL}/v1/resolve/{entity}"
        payload = {"criteria": [criteria]}

        print(f"\n{'=' * 50}")
        print(f"Testing {entity.upper()} (3 attempts)")
        print(f"{'=' * 50}")

        for attempt in range(1, 4):
            print(f"\n  Attempt {attempt}:")
            start = time.time()
            try:
                with httpx.Client(timeout=30) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    elapsed = time.time() - start
                    print(f"    Status: {resp.status_code}")
                    print(f"    Time: {elapsed:.3f}s")
                    if resp.status_code == 200:
                        data = resp.json()
                        print(f"    Response: {json.dumps(data, indent=6)[:200]}")
                    elif resp.status_code in (503, 504):
                        print(
                            "    ERROR: Load balancer error (service may be unhealthy)"
                        )
                    else:
                        print(f"    Response: {resp.text[:200]}")
            except httpx.TimeoutException:
                elapsed = time.time() - start
                print(f"    TIMEOUT after {elapsed:.3f}s")
            except Exception as e:
                elapsed = time.time() - start
                print(f"    ERROR: {e}")

            time.sleep(1)  # Wait between attempts

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
