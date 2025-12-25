# Business Model Navigation Troubleshooting Runbook

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| Holders are None | Hydration not performed, detection failure | [Missing Holders](#problem-1-holders-return-none) |
| Empty holder children | Missing subtasks, wrong holder type | [Empty Children](#problem-2-holder-has-no-children) |
| HydrationError raised | API failure, permission issue, detection tier failure | [Hydration Failures](#problem-3-hydration-errors) |
| Wrong entity type detected | Name/emoji mismatch, missing detection fields | [Type Detection](#problem-4-wrong-entity-type-detected) |
| Upward traversal fails | Missing parent, cycle detected, max depth exceeded | [Traversal Errors](#problem-5-upward-traversal-failures) |
| Contact mapping errors | Stub vs full model confusion, missing _business ref | [Model Navigation](#problem-6-contact-mapping-issues) |

## Overview

The business model hierarchy represents a multi-level structure:

```
Business (root)
├── ContactHolder → [Contact, Contact, ...]
├── UnitHolder → [Unit, Unit, ...]
│   └── Unit
│       ├── OfferHolder → [Offer, Offer, ...]
│       └── ProcessHolder → [Process, Process, ...]
├── LocationHolder → [Location, Hours]
├── DNAHolder → [DNA children]
├── ReconciliationHolder → [Reconciliation children]
├── AssetEditHolder → [AssetEdit children]
└── VideographyHolder → [Videography children]
```

**Key concepts**:
- **Stub model**: Holder or entity loaded without children (metadata only)
- **Full model**: Holder or entity with all children hydrated
- **Hydration**: Process of loading holder children from API
- **Detection**: Identifying entity type from task metadata (name, emoji, projects)
- **Upward traversal**: Following parent chain from child to Business root

**When to use this runbook**: When navigating business model hierarchy produces unexpected results, missing data, or errors.

**Related documentation**:
- `/src/autom8_asana/models/business/business.py` - Business model implementation
- `/src/autom8_asana/models/business/hydration.py` - Hydration orchestration
- `/src/autom8_asana/models/business/detection.py` - Entity type detection
- [REF-business-model-navigation](../reference/REF-business-model-navigation.md)
- [TDD-HYDRATION: Business Model Hydration](../design/TDD-HYDRATION.md)

---

## Problem 1: Holders Return None

### Symptoms
- `business.contact_holder` is `None`
- `business.units` returns empty list
- Holder properties not populated after loading
- Expected data not accessible

### Investigation Steps

1. **Check if hydration was performed**
   ```python
   # Did you use from_gid_async with hydrate=True?
   business = await Business.from_gid_async(client, gid, hydrate=True)

   print(f"Contact holder: {business.contact_holder}")
   print(f"Unit holder: {business.unit_holder}")

   # If None, hydration didn't happen or failed silently
   ```

2. **Check for hydration errors**
   ```python
   # Use partial_ok to see what failed
   from autom8_asana.exceptions import HydrationError

   try:
       business = await Business.from_gid_async(client, gid, hydrate=True)
   except HydrationError as e:
       print(f"Hydration failed: {e.message}")
       print(f"Phase: {e.phase}")
       print(f"Entity GID: {e.entity_gid}")
       if e.partial_result:
           print(f"Partial result available: {e.partial_result.failed}")
   ```

3. **Use hydrate_from_gid_async for detailed results**
   ```python
   from autom8_asana.models.business.hydration import hydrate_from_gid_async

   result = await hydrate_from_gid_async(
       client, business_gid, partial_ok=True
   )

   print(f"Is complete: {result.is_complete}")
   print(f"Succeeded branches: {len(result.succeeded)}")
   print(f"Failed branches: {len(result.failed)}")

   for branch in result.succeeded:
       print(f"  ✓ {branch.holder_type}: {branch.child_count} children")

   for failure in result.failed:
       print(f"  ✗ {failure.holder_type}: {failure.error}")
       print(f"    Recoverable: {failure.recoverable}")
   ```

4. **Check Business subtasks exist**
   ```python
   # Verify Business actually has holder subtasks
   subtasks = await client.tasks.subtasks_async(business.gid).collect()
   print(f"Business has {len(subtasks)} subtasks")

   for subtask in subtasks:
       print(f"  - {subtask.name} ({subtask.gid})")

   # Should see: Contacts, Business Units, Location, etc.
   ```

### Resolution

**Hydration not performed**:
- **Cause**: Used `hydrate=False` or manual Task loading
- **Fix**: Use factory method with hydration
  ```python
  # WRONG: Manual loading doesn't hydrate
  task_data = await client.tasks.get_async(business_gid)
  business = Business.model_validate(task_data.model_dump())
  # business.contact_holder will be None

  # RIGHT: Use factory method
  business = await Business.from_gid_async(client, business_gid, hydrate=True)
  # business.contact_holder is populated
  ```

**Holder subtasks don't exist**:
- **Cause**: Business was created without holders, or they were deleted
- **Fix**: Create missing holders
  ```python
  # Check which holders are missing
  from autom8_asana.models.business.business import Business

  expected_holders = Business.HOLDER_KEY_MAP.keys()
  # ['contact_holder', 'unit_holder', 'location_holder', ...]

  actual_holder_names = [st.name for st in subtasks]

  for holder_key, (name, emoji) in Business.HOLDER_KEY_MAP.items():
       if name not in actual_holder_names:
           print(f"Missing holder: {name}")
           # Create it manually if needed
  ```

**Detection failure**:
- **Cause**: Holder name/emoji changed, detection fields missing
- **Fix**: See [Problem 4: Wrong Entity Type Detected](#problem-4-wrong-entity-type-detected)

**Partial hydration failure**:
- **Cause**: Some holders failed to load (permissions, API errors)
- **Fix**: Use `partial_ok=True` to get what's available
  ```python
  result = await hydrate_from_gid_async(
      client, business_gid, partial_ok=True
  )

  business = result.business
  # Some holders may be None, but you get what succeeded

  # Check which holders are available
  available = [b.holder_type for b in result.succeeded]
  failed = [f.holder_type for f in result.failed]

  print(f"Available: {available}")
  print(f"Failed: {failed}")
  ```

### Prevention
- Always use `Business.from_gid_async(client, gid, hydrate=True)` for full model
- Check `result.is_complete` when using `hydrate_from_gid_async`
- Log hydration failures for monitoring
- Validate Business structure after creation
- Use `partial_ok=True` for graceful degradation

---

## Problem 2: Holder Has No Children

### Symptoms
- `contact_holder` is not None but `contacts` is empty
- `business.units` returns `[]`
- Holder exists but appears unpopulated
- Child count is 0

### Investigation Steps

1. **Check if holder is actually populated**
   ```python
   if business.contact_holder is not None:
       print(f"Holder GID: {business.contact_holder.gid}")
       print(f"Contacts: {len(business.contacts)}")

       # Check private attribute directly
       print(f"_contacts: {getattr(business.contact_holder, '_contacts', 'N/A')}")
   ```

2. **Verify holder has subtasks in API**
   ```python
   # Fetch holder's subtasks directly
   if business.contact_holder:
       subtasks = await client.tasks.subtasks_async(
           business.contact_holder.gid
       ).collect()
       print(f"ContactHolder has {len(subtasks)} subtasks")

       for st in subtasks:
           print(f"  - {st.name} ({st.gid})")
   ```

3. **Check if _populate_children was called**
   ```python
   # During hydration, holders should have children populated
   # If empty, hydration may have skipped this holder

   # Manually trigger population (for debugging)
   if business.contact_holder and len(business.contacts) == 0:
       subtasks = await client.tasks.subtasks_async(
           business.contact_holder.gid,
           include_detection_fields=True
       ).collect()

       business.contact_holder._populate_children(subtasks)
       print(f"After manual populate: {len(business.contacts)} contacts")
   ```

4. **Check detection fields**
   ```python
   # Children need detection fields for type identification
   subtasks = await client.tasks.subtasks_async(
       business.contact_holder.gid,
       include_detection_fields=True  # Critical!
   ).collect()

   for st in subtasks:
       # Verify detection fields present
       projects = getattr(st, 'projects', [])
       memberships = getattr(st, 'memberships', [])
       print(f"{st.name}: {len(projects)} projects, {len(memberships)} memberships")
   ```

### Resolution

**Holder truly has no children**:
- **Cause**: Business was created but holders not populated yet
- **Fix**: This is expected for new businesses
  ```python
  # Check if this is a newly created business
  if len(business.contacts) == 0:
      print("Business has no contacts yet - this may be expected")

      # Create first contact if needed
      # (See contact creation documentation)
  ```

**Population failed silently**:
- **Cause**: Exception during _populate_children was caught
- **Fix**: Use partial_ok to see failures
  ```python
  result = await hydrate_from_gid_async(
      client, business_gid, partial_ok=True
  )

  for failure in result.failed:
      if failure.holder_type == "contact_holder":
          print(f"Contact population failed: {failure.error}")
  ```

**Detection fields missing**:
- **Cause**: Subtasks fetched without `include_detection_fields=True`
- **Fix**: Always include detection fields for children
  ```python
  # WRONG: Missing detection fields
  subtasks = await client.tasks.subtasks_async(holder.gid).collect()
  holder._populate_children(subtasks)  # May fail silently

  # RIGHT: Include detection fields
  subtasks = await client.tasks.subtasks_async(
      holder.gid,
      include_detection_fields=True
  ).collect()
  holder._populate_children(subtasks)  # Works correctly
  ```

**Wrong holder type**:
- **Cause**: Holder detected as wrong type, children not matching
- **Fix**: Verify holder identification
  ```python
  # Check holder detection
  from autom8_asana.models.business.detection import detect_entity_type_async

  task_data = await client.tasks.get_async(holder.gid)
  detection = await detect_entity_type_async(task_data, client)

  print(f"Detected as: {detection.entity_type}")
  print(f"Tier: {detection.tier_used}")
  print(f"Confidence: {detection.confidence}")

  # Expected: EntityType.CONTACT_HOLDER, tier 1 or 2, high confidence
  ```

### Prevention
- Always fetch subtasks with `include_detection_fields=True`
- Check `child_count` in HydrationBranch for populated holders
- Log when holders are empty for monitoring
- Validate business structure expectations
- Use factory methods instead of manual population

---

## Problem 3: Hydration Errors

### Symptoms
- `HydrationError` raised during loading
- Error message shows "hydration failed"
- Partial hydration incomplete
- Missing bidirectional references

### Investigation Steps

1. **Identify failure phase**
   ```python
   from autom8_asana.exceptions import HydrationError

   try:
       business = await Business.from_gid_async(client, gid, hydrate=True)
   except HydrationError as e:
       print(f"Phase: {e.phase}")  # "upward" or "downward"
       print(f"Entity GID: {e.entity_gid}")
       print(f"Entity type: {e.entity_type}")
       print(f"Message: {e.message}")

       # Check if partial result available
       if hasattr(e, 'partial_result') and e.partial_result:
           print("Partial result available:")
           print(f"  Succeeded: {len(e.partial_result.succeeded)}")
           print(f"  Failed: {len(e.partial_result.failed)}")
   ```

2. **Check underlying cause**
   ```python
   try:
       business = await Business.from_gid_async(client, gid, hydrate=True)
   except HydrationError as e:
       # HydrationError wraps original exception
       cause = e.__cause__
       print(f"Underlying cause: {type(cause).__name__}")
       print(f"Cause message: {cause}")

       # Common causes:
       # - NotFoundError: GID doesn't exist
       # - ForbiddenError: No permission to access
       # - RateLimitError: Too many API calls
       # - ServerError: Asana API issue
   ```

3. **Check API call count**
   ```python
   result = await hydrate_from_gid_async(
       client, business_gid, partial_ok=True
   )

   print(f"API calls made: {result.api_calls}")
   # High count (>50) may indicate deep hierarchy or retry loops
   ```

4. **Check specific holder failures**
   ```python
   result = await hydrate_from_gid_async(
       client, business_gid, partial_ok=True
   )

   for failure in result.failed:
       print(f"Holder: {failure.holder_type}")
       print(f"  GID: {failure.holder_gid}")
       print(f"  Phase: {failure.phase}")
       print(f"  Error: {failure.error}")
       print(f"  Recoverable: {failure.recoverable}")
   ```

### Resolution

**NotFoundError during hydration**:
- **Cause**: Business or holder was deleted mid-hydration
- **Fix**: Verify GID exists before hydration
  ```python
  # Pre-flight check
  try:
      task = await client.tasks.get_async(business_gid)
      print(f"Business exists: {task.name}")
  except NotFoundError:
      print(f"Business {business_gid} not found")
      # Don't attempt hydration

  # Then hydrate
  business = await Business.from_gid_async(client, business_gid)
  ```

**ForbiddenError during hydration**:
- **Cause**: Insufficient permissions to access some holders
- **Fix**: Use partial_ok to get accessible data
  ```python
  result = await hydrate_from_gid_async(
      client, business_gid, partial_ok=True
  )

  business = result.business
  # Work with what's available

  # Log permission issues
  for failure in result.failed:
      if "ForbiddenError" in str(failure.error):
          print(f"No access to {failure.holder_type}")
  ```

**RateLimitError during hydration**:
- **Cause**: Too many concurrent hydrations or API calls
- **Fix**: Add delay between hydrations
  ```python
  import asyncio

  # Hydrate multiple businesses with delay
  businesses = []
  for business_gid in business_gids:
      business = await Business.from_gid_async(client, business_gid)
      businesses.append(business)

      # Small delay to avoid rate limits
      await asyncio.sleep(0.5)
  ```

**ServerError during hydration**:
- **Cause**: Asana API temporary issue
- **Fix**: Retry with exponential backoff
  ```python
  import asyncio
  from autom8_asana.exceptions import ServerError

  async def hydrate_with_retry(client, gid, max_retries=3):
      for attempt in range(max_retries):
          try:
              return await Business.from_gid_async(client, gid)
          except ServerError as e:
              if attempt < max_retries - 1:
                  wait = 2 ** attempt
                  print(f"Server error, retrying in {wait}s...")
                  await asyncio.sleep(wait)
              else:
                  raise

  business = await hydrate_with_retry(client, business_gid)
  ```

**Deep hierarchy timeout**:
- **Cause**: Very deep unit hierarchy (many units with many offers/processes)
- **Fix**: Increase timeout or hydrate in stages
  ```python
  from autom8_asana.config import AsanaConfig

  # Increase timeout for deep hierarchies
  config = AsanaConfig(timeout=120.0)  # 2 minutes
  client = AsanaClient(token=token, config=config)

  # Or hydrate in stages
  business = await Business.from_gid_async(client, gid, hydrate=False)
  # Manually hydrate specific holders as needed
  await business._fetch_holders_async(client)
  ```

### Prevention
- Use `partial_ok=True` for non-critical paths
- Implement retry logic for transient errors
- Monitor API call counts during hydration
- Set appropriate timeouts for deep hierarchies
- Validate permissions before hydration
- Add circuit breakers for repeated failures

---

## Problem 4: Wrong Entity Type Detected

### Symptoms
- Contact detected as Offer
- Holder detected as regular entity
- UNKNOWN entity type returned
- Detection confidence is LOW

### Investigation Steps

1. **Check detection result**
   ```python
   from autom8_asana.models.business.detection import detect_entity_type_async

   task = await client.tasks.get_async(gid, opt_fields=[
       "name", "custom_fields", "projects.name", "memberships.project.name"
   ])

   detection = await detect_entity_type_async(task, client)

   print(f"Type: {detection.entity_type}")
   print(f"Tier: {detection.tier_used}")
   print(f"Confidence: {detection.confidence}")
   print(f"Fallback used: {detection.fallback_used}")
   ```

2. **Check detection fields present**
   ```python
   task = await client.tasks.get_async(gid, opt_fields=[
       "name", "custom_fields", "projects.name", "memberships.project.name"
   ])

   print(f"Name: {task.name}")
   print(f"Projects: {len(task.projects) if task.projects else 0}")
   print(f"Memberships: {len(task.memberships) if task.memberships else 0}")
   print(f"Custom fields: {len(task.custom_fields) if task.custom_fields else 0}")

   # Tier 1: project.name
   if task.memberships:
       for m in task.memberships:
           print(f"  Project: {m.project.name if m.project else 'N/A'}")
   ```

3. **Check name pattern**
   ```python
   # Holders typically have emoji in name
   import re

   emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]')
   has_emoji = bool(emoji_pattern.search(task.name))

   print(f"Name: {task.name}")
   print(f"Has emoji: {has_emoji}")

   # Expected holder names:
   # "👥 Contacts", "📦 Business Units", "📍 Location", etc.
   ```

4. **Test structure inspection (Tier 4)**
   ```python
   # Force structure inspection
   detection = await detect_entity_type_async(
       task, client, allow_structure_inspection=True
   )

   print(f"With structure: {detection.entity_type}")
   print(f"Tier: {detection.tier_used}")

   # Tier 4 inspects subtasks to determine if holder
   ```

### Resolution

**Missing detection fields**:
- **Cause**: Task fetched without required opt_fields
- **Fix**: Include detection fields
  ```python
  from autom8_asana.models.business.fields import DETECTION_OPT_FIELDS

  # WRONG: Insufficient fields
  task = await client.tasks.get_async(gid, opt_fields=["name"])

  # RIGHT: Include detection fields
  task = await client.tasks.get_async(gid, opt_fields=DETECTION_OPT_FIELDS)
  # DETECTION_OPT_FIELDS includes all needed for detection
  ```

**Name or emoji changed**:
- **Cause**: Holder name modified in Asana, no longer matches pattern
- **Fix**: Update HOLDER_KEY_MAP or use project-based detection
  ```python
  # Check holder name
  from autom8_asana.models.business.business import Business

  for key, (expected_name, emoji) in Business.HOLDER_KEY_MAP.items():
      print(f"{key}: '{expected_name}' with :{emoji}:")

  # If name changed:
  # Option 1: Update HOLDER_KEY_MAP (not recommended - requires code change)
  # Option 2: Rely on project-based detection (Tier 1)
  # Option 3: Enable structure inspection (Tier 4)
  ```

**Project membership missing**:
- **Cause**: Tier 1 detection relies on PRIMARY_PROJECT_GID membership
- **Fix**: Ensure entities in correct project
  ```python
  # Check project membership
  if task.memberships:
      project_gids = [m.project.gid for m in task.memberships if m.project]
      print(f"Member of projects: {project_gids}")

      # Compare to expected PRIMARY_PROJECT_GID
      from autom8_asana.models.business.contact import ContactHolder

      expected = ContactHolder.PRIMARY_PROJECT_GID
      if expected not in project_gids:
          print(f"Warning: Not in expected project {expected}")
  ```

**Fallback to structure inspection needed**:
- **Cause**: Tier 1-3 failed, need Tier 4
- **Fix**: Enable structure inspection
  ```python
  # Allow structure inspection (makes 1 extra API call)
  detection = await detect_entity_type_async(
      task, client, allow_structure_inspection=True
  )

  # This inspects subtasks to determine if entity is a holder
  ```

**UNKNOWN entity type**:
- **Cause**: Entity not recognized by any detection tier
- **Fix**: Manual type specification or extension
  ```python
  # If detection fails, you may need to manually determine type
  # based on business logic

  # Check if it looks like a holder (has subtasks)
  subtasks = await client.tasks.subtasks_async(task.gid).collect()
  is_likely_holder = len(subtasks) > 0

  if is_likely_holder:
      # Determine which holder based on parent
      parent = await client.tasks.get_async(task.parent.gid)
      # Use parent type to infer child holder type
  ```

### Prevention
- Always include DETECTION_OPT_FIELDS when fetching for detection
- Don't modify holder names in Asana
- Ensure entities added to correct projects
- Enable structure inspection for ambiguous cases
- Log detection tier used for monitoring
- Validate detection confidence before proceeding

---

## Problem 5: Upward Traversal Failures

### Symptoms
- "Reached root without finding Business" error
- "Cycle detected" error during traversal
- "Max traversal depth exceeded"
- Cannot find Business from child entity

### Investigation Steps

1. **Check parent chain**
   ```python
   # Manually walk parent chain
   current_gid = contact_gid
   depth = 0
   max_depth = 10

   while depth < max_depth:
       task = await client.tasks.get_async(current_gid)
       print(f"Depth {depth}: {task.name} ({task.gid})")

       if task.parent is None:
           print("Reached root - no parent")
           break

       current_gid = task.parent.gid
       depth += 1

   # Should see: Contact → ContactHolder → Business
   ```

2. **Check for cycles**
   ```python
   visited = set()
   current_gid = entity_gid

   while current_gid:
       if current_gid in visited:
           print(f"CYCLE DETECTED: {current_gid} already visited")
           print(f"Visited path: {visited}")
           break

       visited.add(current_gid)
       task = await client.tasks.get_async(current_gid)

       if task.parent:
           current_gid = task.parent.gid
       else:
           print(f"Root reached: {task.name}")
           break
   ```

3. **Check Business detection at root**
   ```python
   # Get the root entity
   current = await client.tasks.get_async(entity_gid)
   while current.parent:
       current = await client.tasks.get_async(current.parent.gid)

   # Detect if root is Business
   from autom8_asana.models.business.detection import detect_entity_type_async

   detection = await detect_entity_type_async(current, client)
   print(f"Root type: {detection.entity_type}")

   # Expected: EntityType.BUSINESS
   # If not, entity is orphaned or in wrong hierarchy
   ```

4. **Check traversal with debug logging**
   ```python
   import logging

   # Enable debug logging
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger("autom8_asana.models.business.hydration")

   # Traversal logs parent fetches and detection
   from autom8_asana.models.business.hydration import _traverse_upward_async

   business, path = await _traverse_upward_async(entity, client)

   # Check logs for:
   # - "Starting upward traversal"
   # - "Fetching parent task"
   # - "Detected parent type"
   # - "Upward traversal complete"
   ```

### Resolution

**Entity not in business hierarchy**:
- **Cause**: Entity is standalone or in different project structure
- **Fix**: Verify entity belongs to a Business
  ```python
  # Check if entity has proper parent chain
  task = await client.tasks.get_async(entity_gid)

  if task.parent is None:
      print("Entity is a root task - not part of business hierarchy")
      # This entity cannot be traversed to Business

  # Verify parent exists and is accessible
  try:
      parent = await client.tasks.get_async(task.parent.gid)
      print(f"Parent: {parent.name}")
  except NotFoundError:
      print("Parent task does not exist or not accessible")
  ```

**Parent chain broken**:
- **Cause**: Holder or intermediate entity deleted/orphaned
- **Fix**: Reconstruct hierarchy or skip traversal
  ```python
  # If traversal fails, use direct Business loading instead
  # (requires knowing Business GID)

  # Option 1: Store Business GID on entities
  # Option 2: Search for Business by name/custom field
  # Option 3: Reconstruct parent chain manually
  ```

**Cycle in parent chain**:
- **Cause**: Data corruption - task is ancestor of itself
- **Fix**: This is critical data integrity issue
  ```python
  # Report to Asana support - cycles should not be possible

  # Workaround: Skip traversal, load Business directly if known
  # Or manually break cycle by finding Business through search
  ```

**Max depth exceeded**:
- **Cause**: Hierarchy deeper than expected (default max_depth=10)
- **Fix**: Increase max_depth or simplify hierarchy
  ```python
  from autom8_asana.models.business.hydration import _traverse_upward_async

  # Increase max depth
  business, path = await _traverse_upward_async(
      entity, client, max_depth=20
  )

  # Or simplify hierarchy - normal depth is 2-4 levels
  # Business → UnitHolder → Unit → OfferHolder → Offer (depth 4)
  ```

**Business not detected at root**:
- **Cause**: Root is not a Business entity or detection failed
- **Fix**: Verify root is correctly set up as Business
  ```python
  # Check root entity type
  root_task = await client.tasks.get_async(root_gid)
  print(f"Root name: {root_task.name}")

  # Business should have PRIMARY_PROJECT_GID membership
  from autom8_asana.models.business.business import Business

  expected_project = Business.PRIMARY_PROJECT_GID
  if root_task.memberships:
      project_gids = [m.project.gid for m in root_task.memberships]
      if expected_project not in project_gids:
          print(f"Root not in Business project {expected_project}")
          # Add to correct project or fix detection
  ```

### Prevention
- Validate parent chain before traversal
- Don't orphan entities by deleting parents
- Keep hierarchy depth reasonable (2-4 levels)
- Ensure Business entities in correct project
- Log traversal paths for debugging
- Add health checks for hierarchy integrity

---

## Problem 6: Contact Mapping Issues

### Symptoms
- Cannot access contact from offer/process
- `_business` reference is None
- Bidirectional navigation broken
- Contact properties return None

### Investigation Steps

1. **Check bidirectional references**
   ```python
   # From Business down to Contact
   business = await Business.from_gid_async(client, business_gid)
   contact = business.contacts[0] if business.contacts else None

   if contact:
       # Check upward reference
       print(f"Contact._business: {contact._business}")
       # Should reference the Business instance

       # Check if references match
       if contact._business is not None:
           print(f"Same Business? {contact._business is business}")
           # Should be True
   ```

2. **Check holder population**
   ```python
   # Verify ContactHolder._populate_children was called
   if business.contact_holder:
       print(f"Holder populated: {hasattr(business.contact_holder, '_contacts')}")
       print(f"Contact count: {len(business.contacts)}")

       # Check each contact's back-reference
       for i, contact in enumerate(business.contacts):
           has_ref = contact._business is not None
           print(f"Contact {i} has _business ref: {has_ref}")
   ```

3. **Check if using stub vs full model**
   ```python
   # Stub: loaded without hydration
   stub_business = await Business.from_gid_async(
       client, business_gid, hydrate=False
   )
   print(f"Stub holder: {stub_business.contact_holder}")  # None

   # Full: loaded with hydration
   full_business = await Business.from_gid_async(
       client, business_gid, hydrate=True
   )
   print(f"Full holder: {full_business.contact_holder}")  # ContactHolder
   print(f"Contacts: {len(full_business.contacts)}")  # > 0
   ```

4. **Check contact mapping logic**
   ```python
   # Offers/Processes should map to Contacts through custom fields
   if business.unit_holder:
       for unit in business.units:
           if unit.offer_holder:
               for offer in unit.offers:
                   # Offer has primary_contact field
                   primary = getattr(offer, 'primary_contact', None)
                   print(f"Offer {offer.name} primary contact: {primary}")

                   # Contact should be resolvable from business.contacts
   ```

### Resolution

**Missing _business reference**:
- **Cause**: `_populate_children` not called or failed
- **Fix**: Ensure proper hydration
  ```python
  # Verify hydration completed
  result = await hydrate_from_gid_async(client, business_gid)

  if not result.is_complete:
      print("Hydration incomplete:")
      for failure in result.failed:
          if failure.holder_type == "contact_holder":
              print(f"  Contact holder failed: {failure.error}")

  # Check bidirectional refs after hydration
  for contact in result.business.contacts:
      assert contact._business is result.business
  ```

**Stub model confusion**:
- **Cause**: Using partially loaded Business
- **Fix**: Always use full hydration for navigation
  ```python
  # DON'T: Use stub for navigation
  business = await Business.from_gid_async(client, gid, hydrate=False)
  # business.contacts is [] - can't navigate

  # DO: Use full hydration
  business = await Business.from_gid_async(client, gid, hydrate=True)
  # business.contacts populated with back-references
  ```

**Contact mapping incorrect**:
- **Cause**: Custom field value doesn't match actual Contact GID
- **Fix**: Validate contact references
  ```python
  # Check if primary_contact GID exists in business.contacts
  business = await Business.from_gid_async(client, business_gid)

  for unit in business.units:
      for offer in unit.offers:
          primary_gid = getattr(offer, 'primary_contact_gid', None)
          if primary_gid:
              contact = next(
                  (c for c in business.contacts if c.gid == primary_gid),
                  None
              )
              if contact is None:
                  print(f"Offer {offer.name} references missing contact {primary_gid}")
  ```

**HolderFactory pattern issue**:
- **Cause**: Holder not using correct parent_ref setting
- **Fix**: Verify HolderFactory configuration
  ```python
  # ContactHolder should set parent_ref="_contact_holder"
  from autom8_asana.models.business.contact import ContactHolder

  # Check class definition
  import inspect
  source = inspect.getsource(ContactHolder)
  if 'parent_ref="_contact_holder"' in source:
       print("ContactHolder correctly configured")
  else:
       print("WARNING: ContactHolder parent_ref may be wrong")
  ```

### Prevention
- Always use `hydrate=True` for full model navigation
- Validate bidirectional references after hydration
- Check `_business` is not None before navigation
- Use type hints to distinguish stub vs full models
- Log when contact mapping fails
- Add assertions in critical navigation paths

---

## Common Scenarios

### Scenario: Load Business with All Children

```python
from autom8_asana.models.business.business import Business

# Full hydration - all holders and children populated
business = await Business.from_gid_async(client, business_gid, hydrate=True)

# Navigate hierarchy
print(f"Business: {business.name}")
print(f"Contacts: {len(business.contacts)}")
print(f"Units: {len(business.units)}")

for contact in business.contacts:
    print(f"  Contact: {contact.full_name}")
    # contact._business points back to business

for unit in business.units:
    print(f"  Unit: {unit.name}")
    for offer in unit.offers:
        print(f"    Offer: {offer.name}")
        # offer._unit points back to unit
        # offer._unit._business points to business
```

### Scenario: Navigate from Offer to Business

```python
from autom8_asana.models.business.hydration import hydrate_from_gid_async

# Start from any GID in hierarchy
result = await hydrate_from_gid_async(client, offer_gid)

business = result.business
print(f"Found Business: {business.name}")
print(f"Entry type: {result.entry_type}")
print(f"Path length: {len(result.path)}")
print(f"API calls: {result.api_calls}")

# Path shows traversal: Offer → OfferHolder → Unit → UnitHolder → Business
for entity in result.path:
    print(f"  Traversed: {entity.name} ({type(entity).__name__})")
```

### Scenario: Partial Hydration with Graceful Degradation

```python
from autom8_asana.models.business.hydration import hydrate_from_gid_async

# Allow partial failures
result = await hydrate_from_gid_async(
    client, business_gid, partial_ok=True
)

business = result.business

# Check what succeeded
for branch in result.succeeded:
    print(f"✓ {branch.holder_type}: {branch.child_count} children")

# Check what failed
for failure in result.failed:
    print(f"✗ {failure.holder_type}: {failure.error}")

    if failure.recoverable:
        # Could retry later
        print(f"   (recoverable - consider retry)")

# Use what's available
if business.contacts:
    print(f"Working with {len(business.contacts)} contacts")
else:
    print("No contacts available - contact_holder may have failed")
```

### Scenario: Debug Entity Type Detection

```python
from autom8_asana.models.business.detection import detect_entity_type_async
from autom8_asana.models.business.fields import DETECTION_OPT_FIELDS

# Fetch with all detection fields
task = await client.tasks.get_async(gid, opt_fields=DETECTION_OPT_FIELDS)

# Detect type with full diagnostics
detection = await detect_entity_type_async(
    task, client, allow_structure_inspection=True
)

print(f"Entity type: {detection.entity_type}")
print(f"Detection tier: {detection.tier_used}")
print(f"Confidence: {detection.confidence}")
print(f"Fallback used: {detection.fallback_used}")

# Tier meanings:
# 1: Project membership (PRIMARY_PROJECT_GID)
# 2: Name pattern (emoji + name match)
# 3: Custom fields presence
# 4: Structure inspection (subtasks analysis)

if detection.tier_used == 4:
    print("Required structure inspection (made extra API call)")
```

---

## Debugging Checklist

When troubleshooting business model navigation:

- [ ] Verify hydration performed with `hydrate=True`
- [ ] Check if holders are None (hydration failed)
- [ ] Validate holder children populated (not empty)
- [ ] Confirm detection fields included in task fetches
- [ ] Check bidirectional references (_business, _unit, etc.)
- [ ] Verify entity in correct project (PRIMARY_PROJECT_GID)
- [ ] Validate parent chain integrity (no cycles, orphans)
- [ ] Check HydrationResult for failed branches
- [ ] Confirm entity type detection correct
- [ ] Verify API call count reasonable (<50 for full Business)
- [ ] Check for permission issues (ForbiddenError)
- [ ] Validate contact mapping through custom fields
- [ ] Test with partial_ok to isolate failures

---

## Related Documentation

- [Business Model Implementation](/src/autom8_asana/models/business/business.py)
- [Hydration Orchestration](/src/autom8_asana/models/business/hydration.py)
- [Entity Type Detection](/src/autom8_asana/models/business/detection.py)
- [HolderFactory Pattern](/src/autom8_asana/models/business/holder_factory.py)
- [REF-business-model-navigation](../reference/REF-business-model-navigation.md)
- [TDD-HYDRATION Design](../design/TDD-HYDRATION.md)
- [ADR-0068: Type Detection Strategy](../decisions/ADR-0068-detection-strategy.md)
- [ADR-0069: Hydration API Design](../decisions/ADR-0069-hydration-api.md)
- [ADR-0070: Partial Failure Handling](../decisions/ADR-0070-partial-failures.md)
