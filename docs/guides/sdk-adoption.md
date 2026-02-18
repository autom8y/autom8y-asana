# SDK Adoption Guide

This guide covers migrating from common Asana integration patterns to the autom8_asana SDK.

## Migration Paths

- [From asana-python SDK](#from-asana-python-sdk)
- [From Raw HTTP Calls](#from-raw-http-calls)
- [From Internal Wrappers](#from-internal-wrappers)

---

## From asana-python SDK

The official `asana` Python package uses synchronous, imperative patterns. The autom8_asana SDK provides async-first design with typed models and the SaveSession pattern.

### Client Initialization

**Before (asana-python):**
```python
import asana

client = asana.Client.access_token("your_token")
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient

# From environment variable (recommended)
client = AsanaClient()  # Uses ASANA_PAT env var

# Explicit token
client = AsanaClient(token="your_token")

# Async context manager (recommended)
async with AsanaClient() as client:
    # operations...
    pass
```

### Reading Tasks

**Before (asana-python):**
```python
import asana

client = asana.Client.access_token("token")

# Get single task
task = client.tasks.find_by_id("task_gid")
print(task["name"])

# List tasks (returns generator)
tasks = client.tasks.find_all(project="project_gid")
for task in tasks:
    print(task["name"])
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient
import asyncio

async def main():
    async with AsanaClient() as client:
        # Get single task (typed model)
        task = await client.tasks.get_async("task_gid")
        print(task.name)  # IDE autocomplete works!

        # List tasks (async iterator with pagination)
        async for task in client.tasks.list_async(project="project_gid"):
            print(task.name)

        # Or collect all at once
        all_tasks = await client.tasks.list_async(project="project_gid").collect()

asyncio.run(main())
```

### Updating Tasks

**Before (asana-python):**
```python
import asana

client = asana.Client.access_token("token")

# Direct API call for each update
client.tasks.update("task_gid", {"name": "New Name"})
client.tasks.update("task_gid", {"notes": "Updated notes"})

# Adding a tag requires separate call
client.tasks.add_tag("task_gid", {"tag": "tag_gid"})
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
import asyncio

async def main():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            session.track(task)

            # Multiple changes batched into single API call
            task.name = "New Name"
            task.notes = "Updated notes"

            # Tags via action method
            session.add_tag(task, "tag_gid")

            # Single commit for all changes
            result = await session.commit_async()

asyncio.run(main())
```

### Creating Tasks

**Before (asana-python):**
```python
import asana

client = asana.Client.access_token("token")

task = client.tasks.create({
    "name": "New Task",
    "projects": ["project_gid"],
    "notes": "Task description"
})
print(task["gid"])
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
from autom8_asana.models import Task
import asyncio

async def main():
    async with AsanaClient() as client:
        async with SaveSession(client) as session:
            # Create with typed model
            new_task = Task(
                name="New Task",
                notes="Task description"
            )
            session.track(new_task)

            # Add to project via action method
            session.add_to_project(new_task, "project_gid")

            result = await session.commit_async()

            # GID is populated after commit
            print(new_task.gid)

asyncio.run(main())
```

---

## From Raw HTTP Calls

If you're using `requests`, `httpx`, or `aiohttp` directly against the Asana API.

### Simple GET Request

**Before (requests):**
```python
import requests

headers = {"Authorization": "Bearer your_token"}
response = requests.get(
    "https://app.asana.com/api/1.0/tasks/task_gid",
    headers=headers
)
response.raise_for_status()
task = response.json()["data"]
print(task["name"])
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient
import asyncio

async def main():
    async with AsanaClient(token="your_token") as client:
        task = await client.tasks.get_async("task_gid")
        print(task.name)

asyncio.run(main())
```

### PUT Request

**Before (httpx):**
```python
import httpx

headers = {"Authorization": "Bearer your_token"}
async with httpx.AsyncClient() as http:
    response = await http.put(
        "https://app.asana.com/api/1.0/tasks/task_gid",
        headers=headers,
        json={"data": {"name": "Updated Name"}}
    )
    response.raise_for_status()
    updated = response.json()["data"]
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
import asyncio

async def main():
    async with AsanaClient(token="your_token") as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            session.track(task)
            task.name = "Updated Name"
            await session.commit_async()

asyncio.run(main())
```

### Pagination

**Before (manual pagination):**
```python
import requests

headers = {"Authorization": "Bearer your_token"}
tasks = []
offset = None

while True:
    params = {"project": "project_gid", "limit": 100}
    if offset:
        params["offset"] = offset

    response = requests.get(
        "https://app.asana.com/api/1.0/tasks",
        headers=headers,
        params=params
    )
    response.raise_for_status()
    data = response.json()

    tasks.extend(data["data"])

    if "next_page" not in data or not data["next_page"]:
        break
    offset = data["next_page"]["offset"]

print(f"Found {len(tasks)} tasks")
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient
import asyncio

async def main():
    async with AsanaClient(token="your_token") as client:
        # Automatic pagination
        tasks = await client.tasks.list_async(project="project_gid").collect()
        print(f"Found {len(tasks)} tasks")

        # Or stream for memory efficiency
        count = 0
        async for task in client.tasks.list_async(project="project_gid"):
            count += 1
        print(f"Found {count} tasks")

asyncio.run(main())
```

---

## From Internal Wrappers

If your codebase has custom Asana wrapper classes.

### Legacy Wrapper Pattern

**Before (custom wrapper):**
```python
# Old internal wrapper
class AsanaAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://app.asana.com/api/1.0"

    def get_task(self, task_gid):
        # Custom HTTP handling
        return self._request("GET", f"/tasks/{task_gid}")

    def update_task(self, task_gid, data):
        return self._request("PUT", f"/tasks/{task_gid}", data=data)

    def _request(self, method, path, data=None):
        # Error handling, retries, etc.
        pass

# Usage
api = AsanaAPI("token")
task = api.get_task("task_gid")
api.update_task("task_gid", {"name": "New Name"})
```

**After (autom8_asana):**
```python
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
import asyncio

async def main():
    async with AsanaClient(token="token") as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            session.track(task)
            task.name = "New Name"
            await session.commit_async()

asyncio.run(main())
```

---

## Key Differences

| Aspect | Old Patterns | autom8_asana SDK |
|--------|-------------|------------------|
| **Concurrency** | Sync-only or manual async | Async-first with sync wrappers |
| **Typing** | Dict access (`task["name"]`) | Typed models (`task.name`) |
| **Batching** | Manual implementation | Automatic with SaveSession |
| **Rate Limiting** | Manual implementation | Built-in token bucket |
| **Retries** | Manual implementation | Built-in exponential backoff |
| **Error Handling** | HTTP status codes | Typed exception hierarchy |
| **Pagination** | Manual offset tracking | Automatic async iterators |

---

## Step-by-Step Migration

### Step 1: Install the SDK

```bash
pip install autom8y-asana
```

### Step 2: Update Client Creation

```python
# Replace any client creation with:
from autom8_asana import AsanaClient

# Recommended: use environment variable
client = AsanaClient()  # Uses ASANA_PAT env var

# Or explicit token
client = AsanaClient(token="your_token")
```

### Step 3: Convert Read Operations

```python
# Old: dict access
task = old_client.get_task("gid")
name = task["name"]

# New: typed models
task = await client.tasks.get_async("gid")
name = task.name  # IDE autocomplete!
```

### Step 4: Convert Writes to SaveSession

```python
# Old: direct API calls
old_client.update_task("gid", {"name": "New"})
old_client.add_tag("gid", "tag_gid")

# New: SaveSession pattern
async with SaveSession(client) as session:
    session.track(task)
    task.name = "New"
    session.add_tag(task, "tag_gid")
    await session.commit_async()
```

### Step 5: Update Error Handling

```python
# Old: HTTP status codes
try:
    task = old_client.get_task("gid")
except HttpError as e:
    if e.status_code == 404:
        print("Not found")

# New: typed exceptions
from autom8_asana.exceptions import NotFoundError

try:
    task = await client.tasks.get_async("gid")
except NotFoundError:
    print("Not found")
```

### Step 6: Add Caching (Optional)

```python
from autom8_asana import AsanaClient
from autom8_asana.cache import RedisCacheProvider

cache = RedisCacheProvider(redis_url="redis://localhost:6379/0")
client = AsanaClient(cache=cache)
```

---

## Common Migration Patterns

### Fetch and Update Pattern

**Before:**
```python
task = api.get_task(gid)
task["name"] = "Updated"
api.update_task(gid, task)
```

**After:**
```python
task = await client.tasks.get_async(gid)
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()
```

### Bulk Update Pattern

**Before:**
```python
for task_gid in task_gids:
    api.update_task(task_gid, {"completed": True})
```

**After:**
```python
async with SaveSession(client) as session:
    for task_gid in task_gids:
        task = await client.tasks.get_async(task_gid)
        session.track(task)
        task.completed = True

    result = await session.commit_async()
    print(f"Updated {len(result.succeeded)} tasks")
```

### Dependency Creation Pattern

**Before:**
```python
# Create parent then child
parent = api.create_task({"name": "Parent"})
child = api.create_task({
    "name": "Child",
    "parent": parent["gid"]
})
```

**After:**
```python
from autom8_asana.models import Task

async with SaveSession(client) as session:
    parent = Task(name="Parent")
    child = Task(name="Child")

    session.track(parent)
    session.track(child)

    # Set parent-child relationship
    session.set_parent(child, parent)

    # Parent is automatically saved first due to dependency ordering
    await session.commit_async()
```

---

## Troubleshooting Migration

### "TypeError: object dict can't be used in 'await' expression"

You're mixing old sync code with new async code. Use `async with` and `await`:

```python
# Wrong
task = client.tasks.get_async("gid")  # Missing await

# Correct
task = await client.tasks.get_async("gid")
```

### "AttributeError: 'dict' object has no attribute 'name'"

You're accessing the response as a dict instead of a typed model:

```python
# Wrong (dict access)
name = task["name"]

# Correct (model access)
name = task.name
```

### "UnsupportedOperationError: Direct modification of 'tags' is not supported"

You're modifying a relationship field directly:

```python
# Wrong
task.tags.append(tag)

# Correct
session.add_tag(task, tag)
```

### "SyncInAsyncContextError"

You're calling sync methods from an async context:

```python
# Wrong (in async function)
result = session.commit()

# Correct
result = await session.commit_async()
```

### "SessionClosedError"

You're using a session after it's closed:

```python
# Wrong
async with SaveSession(client) as session:
    session.track(task)

session.track(another_task)  # Session closed!

# Correct
async with SaveSession(client) as session:
    session.track(task)
    session.track(another_task)  # Inside context
    await session.commit_async()
```
