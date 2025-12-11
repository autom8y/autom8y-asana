# autom8_asana

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)

Internal Asana SDK with intelligent caching, batch operations, and Unit of Work pattern.

## Installation

```bash
pip install autom8_asana
```

## Quick Start

autom8_asana uses four patterns: **Client** for reading, **SaveSession** for creating and updating fields, and **Action Methods** for managing relationships (tags, projects, followers, dependencies).

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
- **Intelligent Caching**: Redis-backed caching with TTL and staleness detection
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
# Required
export ASANA_PAT="your_personal_access_token"

# Optional for caching
export REDIS_URL="redis://localhost:6379/0"
```

## License

MIT License - see LICENSE file for details.
