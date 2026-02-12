# autom8_asana SDK Examples

Runnable examples demonstrating common SDK usage patterns.

## Prerequisites

- Python 3.10 or higher
- autom8_asana package installed
- Asana Personal Access Token (PAT)

## Setup

Set your Asana PAT as an environment variable:

```bash
export ASANA_PAT=your_token_here
```

For examples that interact with specific projects or tasks, also set:

```bash
export PROJECT_GID=your_project_gid     # For 01-read-tasks.py
export TARGET_GID=your_task_gid         # For 05-entity-write.py
export API_BASE_URL=http://localhost:8000  # For API examples (08, 09, 10)
export SERVICE_TOKEN=your_jwt_token     # For 09-cache-warming.py
export WEBHOOK_TOKEN=your_webhook_secret  # For 10-webhook-handler.py
```

## Running Examples

All examples use the virtual environment Python:

```bash
.venv/bin/python docs/examples/01-read-tasks.py
```

## Examples

### Beginner Examples

- **01-read-tasks.py** - Fetch tasks from a project, list custom field values
- **02-batch-update.py** - Efficient batch updates with error handling

### Intermediate Examples

- **04-entity-resolution.py** - Resolve entity types and navigate relationships
- **05-entity-write.py** - Write custom fields using the entity write API

### Advanced Examples

- **08-dataframe-export.py** - Export task data as DataFrames (JSON and Polars formats)
- **09-cache-warming.py** - Trigger cache refresh and inspect cache metrics
- **10-webhook-handler.py** - Receive and process Asana webhook events

## Common Patterns

### Async vs Sync

Most SDK methods support both async and sync patterns:

```python
# Async (recommended)
task = await client.tasks.get_async("task_gid")

# Sync (blocks until complete)
task = client.tasks.get("task_gid")
```

### Error Handling

All examples include basic error handling. For production use, see example 10 for comprehensive patterns.

### Environment Variables

Examples read configuration from environment variables to avoid hardcoding credentials. Never commit tokens or GIDs to version control.
