# autom8y-asana SDK Examples

This directory contains runnable examples demonstrating the key features of the autom8y-asana SDK. Each example is a standalone Python script with clear documentation and usage instructions.

## Quick Start

### Prerequisites

1. **Asana Personal Access Token (PAT)**
   - Log in to Asana
   - Go to [My Settings → Apps → Personal Access Tokens](https://app.asana.com/0/my-apps)
   - Click "Create New Token"
   - Copy the token (you'll only see it once)

2. **Set Environment Variable**
   ```bash
   export ASANA_PAT="your_token_here"
   ```

3. **Install the SDK**
   ```bash
   pip install -e .  # From repository root
   # or
   pip install autom8y-asana  # When published to PyPI
   ```

## Configuration

Most examples require workspace and/or project GIDs. You can provide these via:
1. **Environment variables** (recommended) - set once and run all examples
2. **Command-line arguments** - override defaults on a per-run basis

### Setting Default GIDs (Recommended)

Set environment variables to avoid passing GIDs every time:

```bash
# Bash/Zsh (add to ~/.bashrc or ~/.zshrc for persistence)
export ASANA_WORKSPACE_GID="your_workspace_gid"
export ASANA_PROJECT_GID="your_project_gid"

# Now run examples without arguments
python examples/02_task_crud.py
python examples/03_pagination.py
```

### Finding Your GIDs

**Method 1: From Asana Web URL**

Open any project in Asana. The GID is in the URL:
```
https://app.asana.com/0/WORKSPACE_GID/PROJECT_GID
                        ^^^^^^^^^^^^^^  ^^^^^^^^^^^
```

**Method 2: Using the SDK**

```python
from autom8_asana import AsanaClient
import asyncio

async def find_gids():
    async with AsanaClient() as client:
        # Find workspace GID
        workspaces = await client.workspaces.list_async().collect()
        for ws in workspaces:
            print(f"Workspace: {ws.name} → {ws.gid}")

        # Find project GID (replace WORKSPACE_GID)
        projects = await client.projects.list_async(
            workspace="WORKSPACE_GID"
        ).take(10)
        for proj in projects:
            print(f"Project: {proj.name} → {proj.gid}")

asyncio.run(find_gids())
```

### Using direnv (Optional)

For project-specific configuration, use [direnv](https://direnv.net/):

```bash
# Install direnv
brew install direnv  # macOS
# or: apt-get install direnv  # Linux

# Create .envrc in project root
cat > .envrc << EOF
export ASANA_WORKSPACE_GID="your_workspace_gid"
export ASANA_PROJECT_GID="your_project_gid"
EOF

# Allow direnv to load the file
direnv allow
```

Now environment variables load automatically when you `cd` into the project.

### Overriding Defaults

Command-line arguments always take precedence:

```bash
# Use default workspace from env var
python examples/02_task_crud.py

# Override with different workspace
python examples/02_task_crud.py --workspace OTHER_WORKSPACE_GID
```

## Examples Index

### Priority 1: Foundation (Start Here)

**[01_basic_setup.py](./01_basic_setup.py)** - Authentication Methods
- Three ways to authenticate (env var, explicit token, custom provider)
- Getting current user information
- Simplest SDK usage

```bash
python examples/01_basic_setup.py
```

**[02_task_crud.py](./02_task_crud.py)** - Task CRUD Operations
- Create, read, update, delete tasks
- Typed models vs raw dict access
- Both async and sync API patterns

```bash
python examples/02_task_crud.py --workspace WORKSPACE_GID
```

**[03_pagination.py](./03_pagination.py)** - Pagination with PageIterator
- Lazy pagination with `async for`
- Collecting all items with `.collect()`
- Taking first N items with `.take(n)`
- Memory-efficient iteration

```bash
python examples/03_pagination.py --project PROJECT_GID
```

### Priority 2: autom8 Critical Path

**[04_batch_create.py](./04_batch_create.py)** - Batch Task Creation
- Bulk create 50+ tasks efficiently
- Automatic chunking (10 per batch)
- Partial failure handling
- Performance comparison vs sequential

```bash
python examples/04_batch_create.py --project PROJECT_GID
```

**[05_batch_update.py](./05_batch_update.py)** - Batch Task Updates
- Bulk status changes and reassignments
- BatchSummary statistics
- Mixed success/failure scenarios

```bash
python examples/05_batch_update.py --project PROJECT_GID
```

**[06_custom_fields.py](./06_custom_fields.py)** - Custom Fields Management
- Create enum custom fields (Priority, Status, etc.)
- Set and read custom field values
- Other field types (text, number, date)

```bash
python examples/06_custom_fields.py --workspace WORKSPACE_GID --project PROJECT_GID
```

**[07_projects_sections.py](./07_projects_sections.py)** - Projects and Sections
- Create projects with sections
- Move tasks between sections
- Hierarchical organization

```bash
python examples/07_projects_sections.py --workspace WORKSPACE_GID
```

**[12_save_session_basics.py](./12_save_session_basics.py)** - SaveSession Unit of Work Pattern
- Track-modify-commit workflow
- Action methods for relationships (tags, projects, sections)
- Change tracking and inspection
- Partial failure handling
- API call comparison (batched vs sequential)

```bash
python examples/12_save_session_basics.py --workspace WORKSPACE_GID
```

### Priority 3: Production Ready

**[08_webhooks.py](./08_webhooks.py)** - Webhook Setup and Verification
- Create webhooks for resources
- Verify HMAC-SHA256 signatures
- Handle webhook handshake
- Example event handler

```bash
python examples/08_webhooks.py --project PROJECT_GID --target https://your-server.com/webhook
```

**[09_protocol_adapters.py](./09_protocol_adapters.py)** - Protocol Adapters
- Custom AuthProvider for secret management
- Custom CacheProvider for caching
- Custom LogProvider for logging
- Integration patterns for autom8

```bash
python examples/09_protocol_adapters.py
```

**[10_error_handling.py](./10_error_handling.py)** - Error Handling Patterns
- Exception hierarchy (NotFoundError, RateLimitError, etc.)
- Accessing error details and correlation IDs
- Graceful degradation patterns
- Retry logic

```bash
python examples/10_error_handling.py --workspace WORKSPACE_GID
```

## Feature Coverage

| SDK Feature | Example(s) |
|-------------|-----------|
| Authentication | 01 |
| Task CRUD | 02 |
| Pagination | 03 |
| Batch Create | 04 |
| Batch Update | 05 |
| Custom Fields | 06 |
| Projects/Sections | 07 |
| Webhooks | 08 |
| Protocol Adapters | 09 |
| Error Handling | 10 |
| **SaveSession** | **12** |

| Client | Used In Examples |
|--------|-----------------|
| TasksClient | 02, 03, 04, 05, 07 |
| ProjectsClient | 07 |
| SectionsClient | 07 |
| CustomFieldsClient | 06 |
| UsersClient | 01 |
| WorkspacesClient | 01 |
| WebhooksClient | 08 |
| BatchClient | 04, 05 |

## Common Patterns

### Pattern: Async with Context Manager (Recommended)

```python
from autom8_asana import AsanaClient

async def main():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")
        print(task.name)
```

### Pattern: Sync API (Non-async Codebases)

```python
from autom8_asana import AsanaClient

with AsanaClient() as client:
    task = client.tasks.get("task_gid")  # Note: No _async suffix
    print(task.name)
```

### Pattern: Graceful Error Handling

```python
from autom8_asana.exceptions import NotFoundError

try:
    task = await client.tasks.get_async("task_gid")
except NotFoundError:
    print("Task not found")
    task = None
```

### Pattern: Pagination

```python
# Lazy iteration (memory efficient)
async for task in client.tasks.list_async(project="project_gid"):
    print(task.name)

# Collect all (simple)
all_tasks = await client.tasks.list_async(project="project_gid").collect()

# First N items
first_10 = await client.tasks.list_async(project="project_gid").take(10)
```

### Pattern: Batch Operations

```python
# Batch create
tasks_data = [
    {"name": "Task 1", "projects": ["project_gid"]},
    {"name": "Task 2", "projects": ["project_gid"]},
]
results = await client.batch.create_tasks_async(tasks_data)

# Check results
for result in results:
    if result.success:
        print(f"Created: {result.data['gid']}")
    else:
        print(f"Failed: {result.error}")
```

## Troubleshooting

### "AuthenticationError: Invalid token"

- Verify your ASANA_PAT is set correctly: `echo $ASANA_PAT`
- Check the token hasn't expired
- Ensure token has required permissions

### "NotFoundError: Resource not found"

- Verify the GID is correct (no typos)
- Check you have access to the resource
- Ensure resource hasn't been deleted

### "ImportError: No module named 'autom8_asana'"

- Install the SDK: `pip install -e .` (from repo root)
- Verify virtual environment is activated

### "RateLimitError: Rate limit exceeded"

- The SDK automatically handles rate limiting with retries
- If you still hit limits, add delays between operations
- Check `retry_after` attribute for wait time

### "Cannot use sync context manager in async context"

- Use `async with` instead of `with` in async functions
- Use async methods (`get_async`) not sync methods (`get`)

## Next Steps

1. Start with examples 01-03 to understand the basics
2. Move to 04-07 for common autom8 use cases
3. Review 08-10 for production deployment
4. See `examples/autom8_adapters.py` for autom8-specific integration
5. Read the main SDK documentation in `/docs`

## Reference Documentation

- **SDK API Reference**: See docstrings in `/src/autom8_asana/`
- **Design Decisions**: See `/docs/decisions/` for ADRs
- **Technical Specs**: See `/docs/design/` for TDDs
- **Requirements**: See `/docs/requirements/` for PRDs

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review relevant example code
3. Check SDK documentation and ADRs
4. Contact autom8 team for integration support
