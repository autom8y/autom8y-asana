# autom8y-asana

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)

Internal Asana SDK with intelligent caching, batch operations, and Unit of Work pattern.

## Installation

```bash
pip install autom8y-asana
```

## Quick Start

autom8y-asana uses four patterns: **Client** for reading, **SaveSession** for creating and updating fields, and **Action Methods** for managing relationships (tags, projects, followers, dependencies).

**New to the SDK?** Start with [Core Concepts](docs/guides/concepts.md) to understand the mental model.

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def main():
    client = AsanaClient(token="your-token")
    task = await client.tasks.get_async("task_gid")

    async with SaveSession(client) as session:
        session.track(task)
        task.name = "Updated Name"
        session.add_tag(task, "tag_gid")  # Relationships use action methods
        result = await session.commit_async()
        print(f"Saved: {result.success}")

asyncio.run(main())
```

## Key Features

- **Typed Models**: Full Pydantic v2 models for all Asana resources with IDE autocomplete
- **Batch Operations**: Automatic chunking and parallel execution for bulk create/update
- **SaveSession**: Unit of Work pattern for deferred, dependency-aware saves
- **Intelligent Caching**: Redis-backed caching with TTL, staleness detection, and <1s warm fetch latency
- **Async-First**: Native async/await with sync wrappers for non-async codebases

## Documentation

**Start Here:**
- **[Core Concepts](./docs/guides/concepts.md)**: Mental model and decision tree (read first)
- **[Quick Start Guide](./docs/guides/quickstart.md)**: 5-minute path to working code

**Guides:**
- **[Common Workflows](./docs/guides/workflows.md)**: Recipes for typical operations
- **[Best Practices](./docs/guides/patterns.md)**: Recommended patterns and common mistakes
- **[SaveSession Reference](./docs/guides/save-session.md)**: Complete SaveSession API reference
- **[SDK Adoption](./docs/guides/sdk-adoption.md)**: Migration from other patterns
- **[Examples](./examples/README.md)**: Runnable examples for common use cases

## Requirements

- Python 3.10 or higher
- Asana Personal Access Token (PAT) or OAuth token
- Optional: Redis for caching layer

## Environment Setup

```bash
# Required - Authentication
export ASANA_PAT="your_personal_access_token"

# Optional - Workspace (auto-detected if only one workspace)
export ASANA_WORKSPACE_GID="your_workspace_gid"

# Optional - Caching
export REDIS_URL="redis://localhost:6379/0"
```

### ECS/Platform Deployments

For ECS deployments where secrets are injected with platform naming conventions
(e.g., from AWS Secrets Manager), the SDK supports environment variable indirection:

```bash
# Indirection keys point to the actual env vars containing credentials
export ASANA_TOKEN_KEY="BOT_PAT"           # SDK reads token from BOT_PAT env var
export ASANA_WORKSPACE_KEY="WORKSPACE_GID" # SDK reads workspace from WORKSPACE_GID env var

# Actual credentials (injected by ECS from Secrets Manager)
export BOT_PAT="your_pat_here"
export WORKSPACE_GID="your_workspace_gid"
```

This eliminates the need for env var bridging in ECS task definitions.

## License

MIT License - see LICENSE file for details.
