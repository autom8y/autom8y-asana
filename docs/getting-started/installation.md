# Installation and Setup

Get started with the autom8y-asana SDK in minutes. This guide covers installation, configuration, and your first API call.

## Prerequisites

- **Python 3.10 or higher**
- **Asana Personal Access Token (PAT)** — Generate at [app.asana.com/0/my-apps](https://app.asana.com/0/my-apps) under Personal Access Tokens
- **Workspace GID** (optional) — Auto-detected if you have exactly one workspace

## Installation

### SDK Installation

Install from PyPI:

```bash
pip install autom8y-asana
```

### Development Setup

For contributors or advanced users who want to modify the SDK:

```bash
# Clone the repository
git clone https://github.com/autom8y/autom8y-asana.git
cd autom8y-asana

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

## Environment Variables

Configure the SDK using environment variables. Required and optional variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ASANA_PAT` | Yes* | — | Personal Access Token for authentication |
| `ASANA_WORKSPACE_GID` | No | Auto-detect | Workspace GID (required if you have multiple workspaces) |
| `ASANA_ENVIRONMENT` | No | `development` | Environment hint: `development`, `production`, `staging`, `test` |
| `ASANA_CACHE_PROVIDER` | No | Auto-detect | Cache provider: `memory`, `redis`, `tiered`, `none` |
| `ASANA_CACHE_ENABLED` | No | `true` | Enable/disable caching: `true`, `false` |
| `REDIS_HOST` | No | — | Redis hostname (required if using Redis cache) |
| `REDIS_PORT` | No | `6379` | Redis port |

*Required only if not passing `token` parameter directly to `AsanaClient()`.

### Minimal Configuration

Set only the required token:

```bash
export ASANA_PAT="your_personal_access_token_here"
```

### Multi-Workspace Configuration

If you have multiple workspaces, specify which one to use:

```bash
export ASANA_PAT="your_personal_access_token_here"
export ASANA_WORKSPACE_GID="1234567890123456"
```

### Production Configuration

For production environments with Redis caching:

```bash
export ASANA_PAT="your_personal_access_token_here"
export ASANA_WORKSPACE_GID="1234567890123456"
export ASANA_ENVIRONMENT="production"
export ASANA_CACHE_PROVIDER="redis"
export REDIS_HOST="your-redis-host.example.com"
export REDIS_PORT="6379"
```

## First API Call

### Async Example (Recommended)

```python
import asyncio
from autom8_asana import AsanaClient

async def main():
    # Uses ASANA_PAT environment variable
    async with AsanaClient() as client:
        me = await client.users.me_async()
        print(f"Hello, {me.name}!")
        print(f"Email: {me.email}")

asyncio.run(main())
```

### Sync Example

```python
from autom8_asana import AsanaClient

# Uses ASANA_PAT environment variable
client = AsanaClient()
me = client.users.me()
print(f"Hello, {me.name}!")
print(f"Email: {me.email}")
```

### Using Explicit Token

Pass the token directly instead of using environment variables:

```python
import asyncio
from autom8_asana import AsanaClient

async def main():
    async with AsanaClient(token="your_token_here") as client:
        me = await client.users.me_async()
        print(f"Hello, {me.name}!")

asyncio.run(main())
```

### Specifying Workspace

For accounts with multiple workspaces:

```python
import asyncio
from autom8_asana import AsanaClient

async def main():
    async with AsanaClient(
        token="your_token_here",
        workspace_gid="1234567890123456"
    ) as client:
        me = await client.users.me_async()
        print(f"Hello, {me.name}!")

asyncio.run(main())
```

## Running the API Server

The SDK includes a FastAPI server for webhook handling and REST operations.

### Start the Server

```bash
uvicorn autom8_asana.api.main:create_app --factory --host 0.0.0.0 --port 8000
```

### Verify Health

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T10:30:00Z"
}
```

### Production Server

For production deployments:

```bash
uvicorn autom8_asana.api.main:create_app \
  --factory \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

## Configuration Reference

For detailed configuration options including rate limiting, circuit breakers, retry policies, and cache settings, see [Configuration Reference](../sdk-reference/configuration.md).

## Troubleshooting

### AuthenticationError: Environment variable 'ASANA_PAT' not set

**Cause:** The `ASANA_PAT` environment variable is not configured.

**Solution:** Set the environment variable or pass `token` parameter directly:

```bash
export ASANA_PAT="your_token_here"
```

Or:

```python
client = AsanaClient(token="your_token_here")
```

### AuthenticationError: HTTP 401

**Cause:** Invalid or expired Personal Access Token.

**Solution:**
1. Verify your token is correct
2. Generate a new token at [app.asana.com/0/my-apps](https://app.asana.com/0/my-apps)
3. Update the `ASANA_PAT` environment variable

### ConfigurationError: Multiple workspaces found

**Cause:** Your Asana account has access to multiple workspaces and the SDK cannot auto-detect which one to use.

**Solution:** Specify the workspace explicitly:

```bash
export ASANA_WORKSPACE_GID="1234567890123456"
```

Or pass it to the client:

```python
client = AsanaClient(workspace_gid="1234567890123456")
```

To find your workspace GID:
1. Log into Asana
2. Visit any project URL
3. Extract the first number: `https://app.asana.com/0/WORKSPACE_GID/PROJECT_GID`

### RateLimitError: 429 Too Many Requests

**Cause:** Exceeded Asana's rate limit (1500 requests per minute).

**Solution:** The SDK handles retries automatically with exponential backoff. If you see this error, the SDK has exhausted all retry attempts.

Wait before retrying, or reduce request concurrency:

```python
from autom8_asana import AsanaClient, AsanaConfig, ConcurrencyConfig

config = AsanaConfig(
    concurrency=ConcurrencyConfig(
        read_limit=25,  # Reduce from default 50
        write_limit=10  # Reduce from default 15
    )
)
client = AsanaClient(config=config)
```

### Connection Timeout

**Cause:** Network issues or Asana API unavailable.

**Solution:** Check [status.asana.com](https://status.asana.com) for service status. Adjust timeout configuration if needed:

```python
from autom8_asana import AsanaClient, AsanaConfig, TimeoutConfig

config = AsanaConfig(
    timeout=TimeoutConfig(
        connect=10.0,  # Increase from default 5.0
        read=60.0      # Increase from default 30.0
    )
)
client = AsanaClient(config=config)
```

## Next Steps

- [API Basics](./api-basics.md) — Learn core SDK concepts
- [Tasks and Projects](./tasks-and-projects.md) — Work with Asana resources
- [Configuration Reference](../sdk-reference/configuration.md) — Detailed configuration options
- [Examples](../../examples/) — Browse code examples
