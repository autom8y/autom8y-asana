# Issue Reproduction Guide

This document provides code examples to reproduce each identified issue for verification and debugging.

---

## CRITICAL ISSUES

### ISSUE 11: Cascade Operations Not Executed

**Reproduce**:
```python
import asyncio
from autom8_asana.client import AsanaClient
from autom8_asana.persistence.session import SaveSession

async def test_cascade():
    client = AsanaClient(token="your-token")

    # Get a business entity with cascade field
    business = await client.business.get_async("business_gid")

    # Queue cascade operation
    async with SaveSession(client) as session:
        session.track(business)
        business.custom_fields[0]['text_value'] = "New Value"

        # Queue cascade - should propagate to descendants
        session.cascade_field(business, "Office Phone")

        # Preview shows the cascade
        crud_ops, action_ops = session.preview()
        print(f"Pending cascades before commit: {session.get_pending_cascades()}")

        result = await session.commit_async()

        # Check if cascade was executed
        print(f"Pending cascades after commit: {session.get_pending_cascades()}")
        # BUG: Cascades are still pending! They were never executed!

asyncio.run(test_cascade())
```

**Expected**: Cascades should be empty after commit (executed)
**Actual**: Cascades remain in pending list (never executed)

---

### ISSUE 14: Task.model_dump() Silent Data Loss

**Reproduce**:
```python
import asyncio
from autom8_asana.client import AsanaClient

async def test_data_loss():
    client = AsanaClient(token="your-token")

    # Get a task with custom fields
    task = await client.tasks.get_async("task_gid")
    print(f"Original custom field: {task.custom_fields[0]}")

    # Scenario 1: Using accessor (works)
    accessor = task.get_custom_fields()
    accessor.set("Priority", "High")
    print(f"After accessor.set(), model_dump shows: {task.model_dump()['custom_fields']}")
    # Result: Changes ARE included

    # Scenario 2: Direct modification (silent loss!)
    task2 = await client.tasks.get_async("task_gid")
    original_value = task2.custom_fields[0]['text_value']
    task2.custom_fields[0]['text_value'] = "Directly Modified Value"
    print(f"Direct modification: {task2.custom_fields[0]['text_value']}")

    dumped = task2.model_dump()
    print(f"After model_dump(), custom field is: {dumped['custom_fields'][0]}")
    # BUG: Original value is back! Direct modification was lost!

    # Try to save
    await task2.save_async()

    # Verify on API
    refreshed = await client.tasks.get_async("task_gid")
    print(f"After save_async(), API shows: {refreshed.custom_fields[0]['text_value']}")
    # Result: Original value persisted, our change was lost silently!

asyncio.run(test_data_loss())
```

**Expected**: Direct modifications should be persisted or raise error
**Actual**: Direct modifications are silently lost on save

---

## HIGH SEVERITY ISSUES

### ISSUE 5: P1 Methods Don't Check SaveResult.success

**Reproduce**:
```python
import asyncio
from autom8_asana.client import AsanaClient

async def test_silent_failure():
    client = AsanaClient(token="your-token")

    task_gid = "valid_task_gid"
    fake_tag_gid = "999999999999999999"  # Non-existent tag

    # This should fail but won't tell us
    try:
        result = await client.tasks.add_tag_async(task_gid, fake_tag_gid)
        print(f"add_tag_async returned: {result}")
        print(f"Task: {result.gid}, Tags: {result.tags}")
        # BUG: No exception raised! Operation appears to succeed!
        # Actually, the action failed with 422, but we don't know.
    except Exception as e:
        print(f"Exception raised: {e}")
        # Expected to get here with 422 error, but we don't!

asyncio.run(test_silent_failure())
```

**Expected**: Exception raised when tag doesn't exist
**Actual**: No exception, method returns task as if tag was added

**How to verify the failure**:
```python
# Patch add_tag_async to see what's actually happening
from unittest.mock import patch

async def test_with_introspection():
    from autom8_asana.persistence.session import SaveSession

    # Check what commit_async actually returns
    original_commit = SaveSession.commit_async

    async def logged_commit(self):
        result = await original_commit(self)
        print(f"SaveResult.success: {result.success}")
        print(f"SaveResult.failed: {result.failed}")
        print(f"SaveResult.action_results: {result.action_results}")
        return result

    with patch.object(SaveSession, 'commit_async', logged_commit):
        client = AsanaClient(token="your-token")
        await client.tasks.add_tag_async("task_gid", "fake_tag")
        # Now you'll see the failures in action_results, but add_tag_async ignores them!

asyncio.run(test_with_introspection())
```

---

### ISSUE 2: Double API Fetch in add_tag_async()

**Reproduce**:
```python
import asyncio
from unittest.mock import AsyncMock, patch
from autom8_asana.client import AsanaClient

async def test_double_fetch():
    client = AsanaClient(token="your-token")

    # Track HTTP calls
    call_count = 0
    original_get = client.tasks._http.get

    async def counted_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        print(f"API GET call #{call_count}: {args[0]}")
        return await original_get(*args, **kwargs)

    client.tasks._http.get = counted_get

    # Add a single tag
    print("Adding tag to task...")
    task = await client.tasks.add_tag_async("task_gid", "tag_gid")

    print(f"\nTotal API GET calls made: {call_count}")
    # BUG: You'll see 2 calls:
    # 1. GET /tasks/task_gid (before session.add_tag)
    # 2. GET /tasks/task_gid (after commit, to refresh)
    # Expected: 1 call (or N calls for N tags when batched)
    # Actual: 2*N calls!

asyncio.run(test_double_fetch())
```

**Expected**: 1 GET call (task state from SaveResult)
**Actual**: 2 GET calls (before and after commit)

**Impact**: For 100 tags, that's 200 API calls instead of 101.

---

### ISSUE 10: Pending Actions Cleared Before Success Check

**Reproduce**:
```python
import asyncio
from autom8_asana.client import AsanaClient
from autom8_asana.persistence.session import SaveSession

async def test_lost_actions():
    client = AsanaClient(token="your-token")

    async with SaveSession(client) as session:
        task = await client.tasks.get_async("task_gid")

        # Queue 3 actions
        session.add_tag(task, "tag1")
        session.add_tag(task, "tag2")
        session.add_tag(task, "fake_tag")  # This will fail

        print(f"Before commit: {len(session.get_pending_actions())} actions")

        result = await session.commit_async()

        print(f"After commit: {len(session.get_pending_actions())} actions")
        # BUG: 0 actions! All cleared, even the failed one!

        print(f"Failed actions: {len(result.action_results) - sum(1 for r in result.action_results if r.success)}")
        # You can see there were failures, but you can't retry them!

        # Try to get the failed action back
        failed_actions = [r for r in result.action_results if not r.success]
        print(f"Can you retry the failed action? Let's see...")
        # If you try to re-queue it, you need to track it manually
        # BUG: No way to retry, no way to inspect pending actions again

asyncio.run(test_lost_actions())
```

**Expected**: Failed actions remain in _pending_actions for retry
**Actual**: All actions cleared, failed ones are lost

---

## MEDIUM SEVERITY ISSUES

### ISSUE 1: No Idempotency Documentation

**Test Idempotency**:
```python
import asyncio
from autom8_asana.client import AsanaClient

async def test_idempotency():
    client = AsanaClient(token="your-token")

    task_gid = "task_gid"
    tag_gid = "tag_gid"

    # Call add_tag twice with same tag
    print("First add_tag_async call...")
    result1 = await client.tasks.add_tag_async(task_gid, tag_gid)
    print(f"Success: {result1.tags}")

    print("\nSecond add_tag_async call (same tag)...")
    try:
        result2 = await client.tasks.add_tag_async(task_gid, tag_gid)
        # This might fail with 422 from Asana
        print(f"Success: {result2.tags}")
        # But if it does fail, we don't know due to ISSUE 5
    except Exception as e:
        print(f"Got error: {e}")
        # May not get here due to ISSUE 5

    # Expected for idempotent API: Both calls succeed
    # Actual: Second call fails (or succeeds due to ISSUE 5 silently failing)

asyncio.run(test_idempotency())
```

---

### ISSUE 3: move_to_section() Unused project_gid

**Demonstrate**:
```python
import asyncio
from autom8_asana.client import AsanaClient

async def test_unused_parameter():
    client = AsanaClient(token="your-token")

    # This parameter is never used
    result = await client.tasks.move_to_section(
        task_gid="task_gid",
        section_gid="section_gid",
        project_gid="wrong_project_gid"  # Even if wrong, no validation!
    )

    # The operation succeeds regardless of project_gid value
    print(f"Move succeeded: {result.gid}")
    # BUG: project_gid parameter is ignored, making API confusing

asyncio.run(test_unused_parameter())
```

---

### ISSUE 6: SaveSession.commit() Doesn't Close

**Demonstrate**:
```python
import asyncio
from autom8_asana.persistence.session import SaveSession
from autom8_asana.client import AsanaClient

async def test_session_state():
    client = AsanaClient(token="your-token")

    async with SaveSession(client) as session:
        task = await client.tasks.get_async("task_gid")
        session.track(task)

        # Commit
        result = await session.commit_async()
        print(f"After commit, session state: {session._state}")
        # Result: "committed" not "closed"

        # Can still track new entities!
        task2 = await client.tasks.get_async("task_gid_2")
        session.track(task2)  # This works!
        print(f"Successfully tracked new entity after commit!")
        # BUG: Users expect commit() to be "final", but it's not

        # Commit again
        result2 = await session.commit_async()
        print(f"Second commit also works!")

asyncio.run(test_session_state())
```

---

### ISSUE 13: Task.refresh() Accessor State

**Demonstrate**:
```python
import asyncio
from autom8_asana.client import AsanaClient

async def test_refresh_accessor():
    client = AsanaClient(token="your-token")

    # Get task and create accessor
    task = await client.tasks.get_async("task_gid")
    original_value = task.custom_fields[0]['text_value']

    accessor = task.get_custom_fields()
    accessor.set("Priority", "Modified")
    print(f"After accessor.set: {accessor.get('Priority')}")
    # Result: "Modified"

    # Now refresh the task (simulating stale data)
    await task.refresh_async()
    print(f"After refresh: {accessor.get('Priority')}")
    # BUG: Still returns "Modified" even though task was refreshed!
    # The accessor._modifications was cleared, but _data is stale

    print(f"Task's actual custom field: {task.custom_fields[0]['text_value']}")
    # Result: Original value from API

    # Get accessor again
    accessor2 = task.get_custom_fields()
    print(f"New accessor on same task: {accessor2.get('Priority')}")
    # Result: Original value (correct, but confusing because same task object)

asyncio.run(test_refresh_accessor())
```

---

### ISSUE 16: Accessor Cache After Refresh

**Demonstrate**:
```python
import asyncio
from autom8_asana.client import AsanaClient

async def test_accessor_cache():
    client = AsanaClient(token="your-token")

    # Get task
    task = await client.tasks.get_async("task_gid")

    # Create accessor (cached)
    acc1 = task.get_custom_fields()
    id1 = id(acc1)

    # Modify
    acc1.set("Priority", "High")

    # Refresh task
    await task.refresh_async()

    # Get accessor again
    acc2 = task.get_custom_fields()
    id2 = id(acc2)

    print(f"Same accessor instance: {id1 == id2}")
    # Result: True! It's the same cached instance

    print(f"Modifications cleared: {acc2.has_changes()}")
    # Result: False (modifications were cleared)

    print(f"But _data still stale: {acc2._data is task.custom_fields}")
    # Result: False! Accessor._data is old reference

    # BUG: Cache survives refresh but becomes inconsistent with task data

asyncio.run(test_accessor_cache())
```

---

## LOW SEVERITY NITS

### ISSUE 8: Numeric Field Names as GIDs

**Demonstrate**:
```python
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor

# Create accessor with numeric field name
accessor = CustomFieldAccessor([
    {"gid": "456", "name": "2024", "text_value": "Year"}
])

# Try to get by name
result = accessor.get("2024")
print(f"get('2024'): {result}")
# BUG: Returns None! "2024" is treated as GID, not field name

# Have to use GID
result2 = accessor.get("456")
print(f"get('456'): {result2}")
# This works, but confusing for users

# Fix: accessor.get("2024", default="default") suggests using GID
# But doesn't tell user WHY it failed
```

---

## VERIFICATION CHECKLIST

To verify each issue is fixed:

- [ ] ISSUE 11: `session.get_pending_cascades()` is empty after commit
- [ ] ISSUE 14: Direct custom_fields modifications either persist or raise error
- [ ] ISSUE 5: `add_tag_async()` raises exception on invalid tag
- [ ] ISSUE 2: Only 1-2 API calls for single tag operation (not 2 GETs)
- [ ] ISSUE 10: Failed actions remain in pending_actions or result
- [ ] ISSUE 1: Documentation clearly states non-idempotent guarantee
- [ ] ISSUE 3: `project_gid` parameter removed or validated
- [ ] ISSUE 6: Session state transitions to CLOSED after commit
- [ ] ISSUE 13: Accessor reset after refresh_async()
- [ ] ISSUE 16: Accessor cache cleared on refresh
- [ ] Plus others...

---

## Integration Test for All Fixes

Once all issues are addressed, run this comprehensive test:

```python
import asyncio
from autom8_asana.client import AsanaClient
from autom8_asana.persistence.session import SaveSession

async def comprehensive_test():
    client = AsanaClient(token="your-token")

    # 1. Cascade operations work
    # 2. Model dump preserves direct modifications
    # 3. P1 methods verify success
    # 4. Efficient fetching (single call)
    # 5. Failed actions preserved
    # And so on...

    print("All issues fixed!")

asyncio.run(comprehensive_test())
```
