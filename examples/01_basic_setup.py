"""Example: Basic Setup and Authentication

Demonstrates:
- Three authentication methods (env var, explicit token, custom provider)
- Getting the current authenticated user
- Simple client creation and usage

Requirements:
- ASANA_PAT environment variable set (for method 1)
- Valid Asana Personal Access Token

Usage:
    # Method 1: Using environment variable
    export ASANA_PAT="your_token_here"
    python examples/01_basic_setup.py

    # Method 2: Using explicit token (pass via --token arg)
    python examples/01_basic_setup.py --token "your_token_here"

Output:
    Current user information (GID, name, email)
"""

import asyncio
import os
from argparse import ArgumentParser

from autom8_asana import AsanaClient


async def method_1_env_var() -> None:
    """Authentication Method 1: Environment Variable (Default)

    This is the simplest method. The SDK automatically reads ASANA_PAT
    from environment variables when no auth is explicitly provided.
    """
    print("\n=== Method 1: Environment Variable ===")

    # No token parameter - SDK uses EnvAuthProvider by default
    async with AsanaClient() as client:
        user = await client.users.me_async()
        print(f"Authenticated as: {user.name} ({user.email})")
        print(f"User GID: {user.gid}")


async def method_2_explicit_token(token: str) -> None:
    """Authentication Method 2: Explicit Token

    Pass token directly to AsanaClient. Useful when you have the token
    from a configuration file or secret manager.
    """
    print("\n=== Method 2: Explicit Token ===")

    # Pass token directly to client
    async with AsanaClient(token=token) as client:
        user = await client.users.me_async()
        print(f"Authenticated as: {user.name} ({user.email})")
        print(f"User GID: {user.gid}")


async def method_3_custom_provider() -> None:
    """Authentication Method 3: Custom AuthProvider

    Implement the AuthProvider protocol to integrate with your own
    secret management system. See examples/autom8_adapters.py for
    production examples.
    """
    print("\n=== Method 3: Custom AuthProvider ===")

    # Simple custom provider that reads from environment variables
    class CustomAuthProvider:
        def get_secret(self, key: str) -> str:
            # The SDK passes the key name (e.g., "ASANA_PAT") as configured
            # in AsanaConfig.token_key. Custom providers should respect this
            # parameter rather than hardcoding key names.
            token = os.getenv(key)
            if not token:
                raise KeyError(f"Environment variable '{key}' not found")
            return token

    async with AsanaClient(auth_provider=CustomAuthProvider()) as client:
        user = await client.users.me_async()
        print(f"Authenticated as: {user.name} ({user.email})")
        print(f"User GID: {user.gid}")
        print("\nNote: See examples/autom8_adapters.py for production-ready")
        print("      AuthProvider implementations.")


async def main(token: str | None) -> None:
    """Run all authentication examples."""
    print("autom8_asana SDK - Basic Setup Examples")

    # Method 1: Environment variable (always runs)
    try:
        await method_1_env_var()
    except Exception as e:
        print(f"Method 1 failed: {e}")
        print("Ensure ASANA_PAT environment variable is set")

    # Method 2: Explicit token (if provided)
    if token:
        await method_2_explicit_token(token)
    else:
        print("\n=== Method 2: Skipped (no --token provided) ===")

    # Method 3: Custom provider
    try:
        await method_3_custom_provider()
    except Exception as e:
        print(f"Method 3 failed: {e}")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Demonstrate basic authentication methods for autom8_asana SDK"
    )
    parser.add_argument(
        "--token",
        help="Asana Personal Access Token (optional, for method 2 demo)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.token))
