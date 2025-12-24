# SaveSession Debugging Runbook

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| "Dependency cycle detected" error | Circular task relationships | [Dependency Cycles](#problem-1-dependency-cycle-errors) |
| Partial save with some tasks failing | Dependency graph errors, API failures | [Partial Failures](#problem-2-partial-save-failures) |
| "Healing failed" messages | Self-healing unable to repair graph | [Healing System Issues](#problem-3-healing-system-failures) |
| Save hangs or times out | Deadlock in dependency resolution | [Deadlocks and Timeouts](#problem-4-save-deadlocks-and-timeouts) |

## Problem 1: Dependency Cycle Errors

### Symptoms
- Exception: `DependencyCycleError: Circular dependency detected`
- Save operation aborted
- Error log shows cycle path (e.g., `A -> B -> C -> A`)
- No tasks saved (operation fails before execution)

### Investigation Steps

1. **Identify the cycle from error message**
   ```python
   # Error message format:
   # DependencyCycleError: Circular dependency detected:
   # task_123 -> task_456 -> task_789 -> task_123

   # Extract task GIDs in cycle
   cycle_gids = ["task_123", "task_456", "task_789"]
   ```

2. **Check task relationships in session**
   ```python
   # Print dependency graph for debugging
   session.print_dependency_graph()

   # Or inspect manually
   for task in session.tasks:
       if task.gid in cycle_gids:
           print(f"{task.gid} depends on: {task.dependencies}")
           print(f"{task.gid} blocks: {task.dependents}")
   ```

3. **Verify Asana task dependencies**
   - Check actual dependencies in Asana UI
   - Look for circular relationships created by users
   - Check if dependencies match session state

4. **Check for implicit dependencies**
   - Parent-child relationships (parent creates before child)
   - Custom field dependencies
   - Project membership dependencies

### Resolution

**If cycle is valid in business logic**:

Cycles are not allowed in Asana task dependencies. If detected, one dependency must be broken:

```python
# Option 1: Remove problematic dependency
task_123.dependencies.remove(task_789)  # Break the cycle

# Option 2: Use SaveSession healing
session.enable_healing()  # Auto-detects and breaks cycles
result = await session.save()
```

**If cycle is data error**:

```python
# Clear invalid dependencies
for task in session.tasks:
    if task.gid in cycle_gids:
        task.dependencies.clear()  # Remove all deps
        task.dependents.clear()

# Manually set correct dependencies
task_123.dependencies = [task_456]  # Linear dependency
```

**If cycle caused by stale data**:

```python
# Refresh tasks from API before modifying
for gid in cycle_gids:
    fresh_task = await client.tasks.get_task(gid)
    # Update session with fresh dependency state

# Or use STRICT freshness mode
session = SaveSession(client, freshness=Freshness.STRICT)
```

### Prevention
- Enable SaveSession healing: `session.enable_healing()`
- Validate dependency graph before adding tasks to session
- Use SaveSession dependency analysis: `session.validate_dependencies()`
- Limit user ability to create complex dependency chains

## Problem 2: Partial Save Failures

### Symptoms
- Some tasks saved successfully, others failed
- Error: `PartialSaveError: 5/10 tasks saved`
- Log shows mixed success/failure results
- Application state inconsistent with Asana

### Investigation Steps

1. **Check save result for failures**
   ```python
   result = await session.save()

   print(f"Succeeded: {len(result.succeeded)}")
   print(f"Failed: {len(result.failed)}")

   # Inspect failures
   for task_gid, error in result.failed.items():
       print(f"Task {task_gid} failed: {error}")
   ```

2. **Identify failure patterns**
   - Are failures related (e.g., all depend on one failed task)?
   - Is failure consistent (same tasks fail each attempt)?
   - Check error types (API errors vs. dependency errors)

3. **Check dependency graph**
   ```python
   # Did dependent tasks fail because prerequisite failed?
   session.print_dependency_graph()

   # Example: Task B depends on Task A
   # If A fails, B should be skipped or fail
   ```

4. **Check API errors in failed tasks**
   ```python
   # Common API errors:
   # - 400: Invalid data (missing required fields)
   # - 403: Permission denied
   # - 404: Parent project/section not found
   # - 429: Rate limited
   ```

### Resolution

**If dependency ordering issue**:

SaveSession should automatically resolve dependencies. If not:

```python
# Manual dependency resolution
session.enable_dependency_resolution()
result = await session.save()

# Or specify explicit save order
await session.save(order=["task_A", "task_B", "task_C"])
```

**If API validation errors**:

```python
# Fix invalid task data
for task_gid, error in result.failed.items():
    task = session.get_task(task_gid)

    # Common fixes
    if "name is required" in str(error):
        task.name = "Default Name"

    if "project not found" in str(error):
        task.projects = [valid_project_gid]

# Retry failed tasks
retry_result = await session.retry_failed()
```

**If permission errors**:

```python
# Check user permissions for failed tasks
# User must have write access to:
# - Task's project
# - Task's parent (if subtask)
# - Custom fields being set

# Resolution: use authorized API client or fix permissions
```

**If transient API failures**:

```python
# Implement retry logic
max_retries = 3
for attempt in range(max_retries):
    result = await session.save()
    if result.all_succeeded():
        break

    # Exponential backoff
    await asyncio.sleep(2 ** attempt)
```

### Prevention
- Enable SaveSession healing: `session.enable_healing()`
- Validate task data before adding to session
- Use `session.validate()` before `session.save()`
- Implement comprehensive error handling
- Monitor partial failure rate (alert if >5%)

## Problem 3: Healing System Failures

### Symptoms
- Warning: `Healing attempted but failed to repair graph`
- Errors persist despite healing enabled
- Log shows healing attempts with no resolution
- Save still fails after healing runs

### Investigation Steps

1. **Check what healing attempted**
   ```python
   # Enable healing debug logging
   import logging
   logging.getLogger("autom8_asana.save.healing").setLevel(logging.DEBUG)

   result = await session.save()

   # Review logs for healing actions:
   # - Dependency cycles broken
   # - Invalid references removed
   # - Orphaned tasks handled
   ```

2. **Identify non-healable issues**
   - Fundamental data errors (e.g., required fields missing)
   - Permission issues (healing can't fix auth)
   - API constraints (e.g., invalid enum values)

3. **Check healing configuration**
   ```python
   # Is healing actually enabled?
   print(f"Healing enabled: {session.healing_enabled}")

   # Check healing strategies active
   print(f"Healing strategies: {session.healing_strategies}")
   ```

4. **Review error types**
   ```python
   # Healing can fix:
   # - Dependency cycles
   # - Missing parent references
   # - Invalid custom field values (reset to default)

   # Healing CANNOT fix:
   # - Missing required fields (name, project)
   # - Permission errors
   # - Rate limiting
   ```

### Resolution

**If healing disabled**:

```python
# Enable healing
session.enable_healing()
result = await session.save()
```

**If healing insufficient**:

```python
# Manual intervention required
# Fix issues healing cannot resolve

for task in session.tasks:
    # Ensure required fields present
    if not task.name:
        task.name = "Untitled Task"

    if not task.projects:
        task.projects = [default_project_gid]

    # Validate custom fields
    for field_gid, value in task.custom_fields.items():
        if not is_valid_value(field_gid, value):
            del task.custom_fields[field_gid]  # Remove invalid

# Retry save
result = await session.save()
```

**If healing creates new issues**:

```python
# Disable aggressive healing
session.disable_healing()

# Or configure healing strategies
session.configure_healing(
    break_cycles=True,  # Fix dependency cycles
    remove_invalid_refs=False,  # Don't auto-remove references
    reset_invalid_fields=False,  # Don't reset fields
)
```

**If healing not detecting issue**:

```python
# Manually invoke validation
issues = session.validate_graph()
print(f"Detected issues: {issues}")

# Apply fixes
for issue in issues:
    session.heal_issue(issue)

# Retry save
result = await session.save()
```

### Prevention
- Always enable healing unless you have specific reason not to
- Validate data before adding to session
- Use type-safe task builders to prevent data errors
- Monitor healing success rate
- Add pre-save validation hooks

## Problem 4: Save Deadlocks and Timeouts

### Symptoms
- Save operation hangs indefinitely
- Timeout error after 60 seconds (default)
- No progress in save operation logs
- Application unresponsive during save

### Investigation Steps

1. **Check for infinite dependency loop**
   ```python
   # Dependency resolution stuck in loop
   session.print_dependency_graph()

   # Look for:
   # - Cycles not detected by cycle checker
   # - Very deep dependency chains (>100 levels)
   # - Circular waits in async operations
   ```

2. **Check async operation state**
   ```python
   # Are there pending async operations?
   import asyncio

   pending_tasks = asyncio.all_tasks()
   print(f"Pending async tasks: {len(pending_tasks)}")

   # Check for hung API calls
   ```

3. **Check for resource deadlocks**
   - Database connection pool exhausted?
   - Redis connection pool exhausted?
   - API client connection limit reached?

4. **Review timeout configuration**
   ```python
   # Default save timeout: 60 seconds
   # Check if reasonable for operation size
   session.save_timeout  # Should be proportional to task count
   ```

### Resolution

**If dependency resolution stuck**:

```python
# Increase timeout for large operations
session.save_timeout = 300  # 5 minutes

# Or process in smaller batches
batch_size = 50
for i in range(0, len(tasks), batch_size):
    batch = tasks[i:i+batch_size]
    batch_session = SaveSession(client)
    batch_session.add_tasks(batch)
    await batch_session.save()
```

**If async deadlock**:

```python
# Cancel hung operations
result = await asyncio.wait_for(
    session.save(),
    timeout=60
)

# Or use asyncio.shield to protect critical operations
result = await asyncio.shield(session.save())
```

**If resource pool exhausted**:

```python
# Increase connection pool sizes
client = AsanaClient(
    token=token,
    max_connections=100,  # Increase from default
    pool_timeout=30,
)

# Or reduce concurrent operations
session.max_concurrent_saves = 10  # Limit parallelism
```

**If infinite loop in dependency resolution**:

```python
# Add depth limit to dependency resolution
session.max_dependency_depth = 50  # Prevent infinite recursion

# Or manually break problematic dependencies
for task in session.tasks:
    if len(task.dependencies) > 10:  # Suspiciously many deps
        task.dependencies = task.dependencies[:5]  # Limit
```

### Prevention
- Set reasonable timeouts based on operation size
- Monitor save operation duration (alert if >2 minutes)
- Limit maximum dependency chain depth
- Process large sessions in batches
- Add async operation monitoring

## Emergency Procedures

### Force Save Individual Tasks

**When session save completely broken**:

```python
# Bypass SaveSession, save tasks individually
for task in session.tasks:
    try:
        if task.gid:  # Update existing
            await client.tasks.update_task(task.gid, task.to_dict())
        else:  # Create new
            await client.tasks.create_task(task.to_dict())
    except Exception as e:
        logger.error(f"Failed to save {task.gid or 'new task'}: {e}")
```

**Impact**:
- Dependencies not honored (may create in wrong order)
- No atomic guarantees (partial failures possible)
- Slower than batch save

### Clear SaveSession and Restart

**When session state corrupted**:

```python
# Abandon current session
session.clear()

# Or create fresh session
new_session = SaveSession(client)
new_session.add_tasks(tasks)  # Re-add tasks

# Enable healing
new_session.enable_healing()

result = await new_session.save()
```

### Debug Save Operation

**Enable maximum debug logging**:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Save with verbose logging
result = await session.save(verbose=True)

# Check logs for:
# - Dependency resolution steps
# - API call details
# - Error stack traces
```

## Related Documentation

- [TDD-0010: Save Orchestration](../design/TDD-0010-save-orchestration.md) - SaveSession architecture and dependency graph
- [PRD-0018: SaveSession Reliability](../requirements/PRD-0018-savesession-reliability.md) - Reliability requirements
- [ADR-0035: Unit of Work Pattern](../decisions/ADR-0035-unit-of-work-pattern.md) - Unit of Work pattern for save operations
- [ADR-0040: Partial Failure Handling](../decisions/ADR-0040-partial-failure-handling.md) - How partial failures are handled
- [PRD-0005: Save Orchestration](../requirements/PRD-0005-save-orchestration.md) - Save operation requirements
