# Detection System Troubleshooting Runbook

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| "Unable to detect entity type" error | Ambiguous task, tier system failed | [Detection Failures](#problem-1-entity-type-detection-failures) |
| Wrong entity type detected | Tier priority incorrect, membership conflicts | [Wrong Type Detected](#problem-2-wrong-entity-type-detected) |
| Detection slow (>500ms) | Excessive API calls, cache misses | [Slow Detection](#problem-3-slow-detection-performance) |
| Tier fallback warnings | Higher tiers failing, using fallback tier | [Tier Fallback Issues](#problem-4-tier-fallback-issues) |

## Problem 1: Entity Type Detection Failures

### Symptoms
- Exception: `DetectionError: Unable to determine entity type for task {gid}`
- Detection returns `None` instead of entity type
- Log shows all detection tiers failed
- Application cannot proceed without entity type

### Investigation Steps

1. **Check task in Asana UI**
   - Open task in Asana web interface
   - Verify task exists and is accessible
   - Check project membership, custom fields, task name

2. **Examine detection tier results**
   ```python
   # Enable debug logging
   import logging
   logging.getLogger("autom8_asana.detection").setLevel(logging.DEBUG)

   entity_type = await detect_entity_type(task_gid)

   # Review logs for each tier:
   # Tier 0 (Custom Field): SKIP/PASS/FAIL
   # Tier 1 (Membership): SKIP/PASS/FAIL
   # Tier 2 (Name Pattern): SKIP/PASS/FAIL
   # Tier 3 (Heuristic): SKIP/PASS/FAIL
   ```

3. **Check task data structure**
   ```python
   task = await client.tasks.get_task(task_gid)

   print(f"Projects: {task.get('memberships', [])}")
   print(f"Custom fields: {task.get('custom_fields', [])}")
   print(f"Name: {task.get('name')}")
   print(f"Parent: {task.get('parent')}")
   ```

4. **Verify detection configuration**
   ```python
   # Check detection config
   # - Custom field GID for entity type
   # - Project mappings for membership tier
   # - Name patterns for pattern matching
   ```

### Resolution

**If task has no indicators**:

Tasks without any type markers cannot be detected. Add indicators:

```python
# Option 1: Set custom field (best practice)
await client.tasks.update_task(
    task_gid,
    {"custom_fields": {ENTITY_TYPE_FIELD_GID: "Business"}}
)

# Option 2: Add to typed project
await client.tasks.add_project(
    task_gid,
    {"project": BUSINESS_PROJECT_GID}
)

# Option 3: Use naming convention
await client.tasks.update_task(
    task_gid,
    {"name": "[Business] Task Name"}
)
```

**If custom field missing**:

```python
# Verify custom field exists and is accessible
custom_fields = await client.custom_fields.get_custom_fields_for_workspace(
    workspace_gid
)

entity_type_field = next(
    (cf for cf in custom_fields if cf["name"] == "Entity Type"),
    None
)

if not entity_type_field:
    # Field doesn't exist, create it or update config
    raise ConfigurationError("Entity Type custom field not found")
```

**If detection config incorrect**:

```python
# Update detection configuration
detection_config = {
    "custom_field_gid": "1234567890123456",  # Correct GID
    "project_mappings": {
        "9876543210987654": "Business",  # Project GID -> Type
        "1111111111111111": "Contact",
    },
    "name_patterns": {
        r"\[Business\]": "Business",
        r"\[Contact\]": "Contact",
    }
}

detector = EntityDetector(client, detection_config)
entity_type = await detector.detect(task_gid)
```

**If fallback needed**:

```python
# Use default entity type for undetectable tasks
try:
    entity_type = await detect_entity_type(task_gid)
except DetectionError:
    entity_type = "Business"  # Safe default
    logger.warning(f"Using default type for {task_gid}")
```

### Prevention
- Require entity type custom field on task creation
- Use task templates that include entity type
- Monitor detection failure rate (alert if >1%)
- Add validation before task creation

## Problem 2: Wrong Entity Type Detected

### Symptoms
- Task detected as wrong entity type (e.g., Contact instead of Business)
- Application logic uses wrong entity behavior
- Data inconsistencies from type mismatch
- User reports entity showing up in wrong views

### Investigation Steps

1. **Verify expected vs. actual type**
   ```python
   detected_type = await detect_entity_type(task_gid)
   expected_type = "Business"  # From business logic

   print(f"Detected: {detected_type}")
   print(f"Expected: {expected_type}")

   if detected_type != expected_type:
       print("MISMATCH!")
   ```

2. **Check which tier matched**
   ```python
   # Review debug logs to see which tier returned result
   # Example:
   # Tier 0 (Custom Field): PASS -> "Contact"
   # Tier 1 (Membership): SKIP (already detected)

   # The first passing tier wins
   ```

3. **Check for conflicting indicators**
   ```python
   task = await client.tasks.get_task(task_gid)

   # Custom field says "Business"
   cf_value = get_custom_field(task, ENTITY_TYPE_FIELD_GID)
   print(f"Custom field: {cf_value}")

   # But task in "Contact" project
   project_gids = [m["project"]["gid"] for m in task["memberships"]]
   print(f"Projects: {project_gids}")

   # Name suggests "Contact"
   print(f"Name: {task['name']}")
   ```

4. **Check tier priority**
   ```python
   # Tier 0 (Custom Field) has highest priority
   # Tier 1 (Membership) next
   # Tier 2 (Name Pattern) next
   # Tier 3 (Heuristic) lowest

   # First tier to match wins
   ```

### Resolution

**If custom field incorrect**:

Custom field has highest priority. Update it:

```python
# Fix custom field value
await client.tasks.update_task(
    task_gid,
    {"custom_fields": {ENTITY_TYPE_FIELD_GID: "Business"}}
)

# Clear cache to refresh detection
await cache.delete(f"detection:result:{task_gid}")

# Re-detect
entity_type = await detect_entity_type(task_gid)
```

**If membership conflict**:

Task in multiple projects with different types:

```python
# Remove from conflicting project
await client.tasks.remove_project(task_gid, wrong_project_gid)

# Or rely on custom field (Tier 0) to override membership
```

**If name pattern false positive**:

```python
# Name pattern matched incorrectly
# Update name to remove misleading pattern

await client.tasks.update_task(
    task_gid,
    {"name": "Corrected Task Name"}  # Remove [Contact] prefix
)

# Or update detection config to fix pattern
name_patterns = {
    r"^\[Business\]": "Business",  # More specific pattern
    r"^\[Contact\]": "Contact",
}
```

**If tier priority needs adjustment**:

Generally, tier priority is correct (custom field > membership > name > heuristic). If you need different behavior, modify detection logic.

### Prevention
- Use custom field as single source of truth
- Avoid conflicting project memberships
- Standardize naming conventions
- Monitor type changes (alert on unexpected changes)
- Add validation on task creation/update

## Problem 3: Slow Detection Performance

### Symptoms
- Detection takes >500ms per task
- Batch detection slow (>5s for 100 tasks)
- High API call volume during detection
- Application performance degraded

### Investigation Steps

1. **Measure detection time**
   ```python
   import time

   start = time.time()
   entity_type = await detect_entity_type(task_gid)
   duration = time.time() - start

   print(f"Detection took {duration*1000:.0f}ms")

   # Expected: <100ms (cache hit), <500ms (cache miss)
   ```

2. **Check cache hit rate**
   ```python
   # Detection should cache results
   # Check Redis or cache provider

   cache_key = f"detection:result:{task_gid}"
   cached = await cache.get(cache_key)

   if cached:
       print("Cache HIT")
   else:
       print("Cache MISS - will fetch from API")
   ```

3. **Count API calls during detection**
   ```python
   # Enable API call logging
   api_calls = []

   # Track calls to:
   # - tasks.get_task() for task data
   # - custom_fields.get_custom_field_settings() for field metadata
   # - projects.get_project() for project info

   # Should be 1-2 calls max per detection
   ```

4. **Check for N+1 queries**
   ```python
   # Detecting 100 tasks should not make 100 separate API calls
   # Batch detection should coalesce into single multi-get

   tasks = await get_tasks_batch(task_gids)
   # Should use tasks.get_batch(), not individual get_task() calls
   ```

### Resolution

**If cache disabled**:

```python
# Enable detection result caching
cache_provider = RedisCacheProvider(redis_url)
detector = EntityDetector(client, cache_provider=cache_provider)

# Results cached for 24 hours (entity type rarely changes)
```

**If cache misses high**:

```python
# Pre-populate cache for known tasks
task_types = {
    "task_123": "Business",
    "task_456": "Contact",
}

for task_gid, entity_type in task_types.items():
    await cache.set(
        f"detection:result:{task_gid}",
        entity_type,
        ttl=86400  # 24 hours
    )
```

**If excessive API calls**:

```python
# Use batch detection for multiple tasks
entity_types = await detect_entity_types_batch(task_gids)

# Instead of:
# for gid in task_gids:
#     entity_type = await detect_entity_type(gid)  # N API calls
```

**If tier evaluation slow**:

```python
# Skip expensive tiers if earlier tier succeeds
# Already implemented in tier system

# Or disable slow tiers
detection_config = {
    "enable_tier_0": True,   # Custom field (fast)
    "enable_tier_1": True,   # Membership (fast)
    "enable_tier_2": False,  # Name pattern (skip if slow)
    "enable_tier_3": False,  # Heuristic (skip if slow)
}
```

### Prevention
- Always use cache for detection results
- Batch detect when processing multiple tasks
- Monitor detection latency (p95 should be <200ms)
- Pre-populate cache for frequently-accessed tasks

## Problem 4: Tier Fallback Issues

### Symptoms
- Warning: `Tier 0 (Custom Field) failed, falling back to Tier 1`
- Multiple tier failures before success
- Detection succeeds but used low-confidence tier
- Inconsistent detection results

### Investigation Steps

1. **Check why higher tiers failing**
   ```python
   # Review logs for tier failure reasons
   # Common failures:
   # - Tier 0: Custom field not set
   # - Tier 1: No project membership
   # - Tier 2: Name doesn't match pattern
   ```

2. **Verify tier configuration**
   ```python
   # Are tier configurations correct?
   detector.config["custom_field_gid"]  # Should be valid GID
   detector.config["project_mappings"]  # Should include all typed projects
   detector.config["name_patterns"]  # Should cover common patterns
   ```

3. **Check task data quality**
   ```python
   task = await client.tasks.get_task(task_gid)

   # Is custom field present but not set?
   cf_settings = task.get("custom_fields", [])
   entity_type_cf = next(
       (cf for cf in cf_settings if cf["gid"] == ENTITY_TYPE_FIELD_GID),
       None
   )

   if entity_type_cf and not entity_type_cf.get("enum_value"):
       print("Custom field exists but has no value")
   ```

4. **Check fallback success rate**
   ```python
   # Monitor tier usage metrics
   # Expected: Tier 0 (custom field) should succeed 95%+ of time
   # If Tier 1+ used frequently, indicates data quality issues
   ```

### Resolution

**If Tier 0 (custom field) often missing**:

```python
# Backfill custom field for existing tasks
tasks = await get_all_tasks()

for task in tasks:
    if not has_entity_type_field(task):
        # Detect using lower tiers
        entity_type = await detect_entity_type_fallback(task.gid)

        # Set custom field
        await client.tasks.update_task(
            task.gid,
            {"custom_fields": {ENTITY_TYPE_FIELD_GID: entity_type}}
        )
```

**If Tier 1 (membership) unreliable**:

```python
# Update project mappings to include all typed projects
detection_config["project_mappings"] = {
    "123": "Business",
    "456": "Contact",
    "789": "Unit",      # Add missing mappings
    "101": "Offer",
}
```

**If Tier 2 (name pattern) too strict**:

```python
# Relax name patterns to match more cases
name_patterns = {
    r"(?i)business": "Business",  # Case-insensitive
    r"(?i)contact": "Contact",
    r"(?i)\b(unit|holder)\b": "Unit",  # Word boundary
}
```

**If fallback tier confidence low**:

```python
# When Tier 3 (heuristic) used, validation recommended
entity_type = await detect_entity_type(task_gid)

if detector.last_tier_used == 3:
    logger.warning(
        f"Low-confidence detection for {task_gid}: {entity_type}. "
        "Consider setting custom field."
    )
```

### Prevention
- Require entity type custom field on task creation
- Monitor tier usage distribution (95%+ should be Tier 0)
- Alert when fallback tiers used frequently
- Backfill custom field for historical tasks
- Add data quality checks in task creation workflows

## Emergency Procedures

### Force Entity Type

**When detection completely broken**:

```python
# Bypass detection, set type manually
task_gid = "1234567890123456"
entity_type = "Business"  # Known correct type

# Option 1: Update custom field (best)
await client.tasks.update_task(
    task_gid,
    {"custom_fields": {ENTITY_TYPE_FIELD_GID: entity_type}}
)

# Option 2: Cache detection result
await cache.set(
    f"detection:result:{task_gid}",
    entity_type,
    ttl=86400
)
```

### Batch Fix Entity Types

**When many tasks have wrong type**:

```python
# Identify affected tasks
wrong_type_tasks = await find_tasks_with_wrong_type()

# Batch update
for task_gid in wrong_type_tasks:
    correct_type = determine_correct_type(task_gid)

    await client.tasks.update_task(
        task_gid,
        {"custom_fields": {ENTITY_TYPE_FIELD_GID: correct_type}}
    )

    # Clear cache
    await cache.delete(f"detection:result:{task_gid}")
```

### Disable Detection Caching

**When cache contains stale results**:

```python
# Temporarily disable cache to force fresh detection
detector = EntityDetector(client, cache_provider=None)

# Or clear detection cache
for task_gid in affected_tasks:
    await cache.delete(f"detection:result:{task_gid}")

# Re-enable cache after fixing data
detector = EntityDetector(client, cache_provider=cache)
```

## Related Documentation

- [TDD-DETECTION](../design/TDD-DETECTION.md) - Detection system architecture and tier system
- [PRD-DETECTION](../requirements/PRD-DETECTION.md) - Detection requirements and use cases
- [ADR-0068: Type Detection Strategy](../decisions/ADR-0068-type-detection-strategy.md) - Why tier-based detection chosen
- [REF-entity-type-table.md](../reference/REF-entity-type-table.md) - Entity type hierarchy and characteristics
