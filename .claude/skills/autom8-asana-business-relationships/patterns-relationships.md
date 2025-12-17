# Relationship Patterns

> Common patterns and anti-patterns for business model relationships

---

## Pattern: Fetch and Iterate

The most common pattern - fetch business, iterate children:

```python
async with client.save_session() as session:
    # Fetch and track
    task = await client.tasks.get(business_gid)
    business = Business.model_validate(task.model_dump())
    session.track(business)  # prefetch_holders=True by default

    # Wait for prefetch
    await session.prefetch_pending()

    # Now iterate safely
    for contact in business.contacts:
        print(f"{contact.full_name}: {contact.contact_email}")

    for unit in business.units:
        print(f"{unit.vertical}: ${unit.mrr}")
```

---

## Pattern: Modify and Save

Modify entities in hierarchy and save:

```python
async with client.save_session() as session:
    session.track(business)
    await session.prefetch_pending()

    # Modify at multiple levels
    business.company_id = "NEW-ID"

    owner = business.contact_holder.owner
    if owner:
        session.track(owner)  # Track specific entity
        owner.contact_phone = "555-1234"

    # Commit all changes
    result = await session.commit_async()
    if result.success:
        print("All changes saved")
```

---

## Pattern: Find Specific Entity

Navigate to find specific child:

```python
def find_contact_by_email(business: Business, email: str) -> Contact | None:
    """Find a contact by email address."""
    for contact in business.contacts:
        if contact.contact_email == email:
            return contact
    return None

def find_unit_by_vertical(business: Business, vertical: str) -> Unit | None:
    """Find first unit matching vertical."""
    for unit in business.units:
        if unit.vertical == vertical:
            return unit
    return None

# Usage
contact = find_contact_by_email(business, "john@example.com")
if contact:
    print(f"Found: {contact.full_name} at {contact.business.name}")
```

---

## Pattern: Cross-Navigation

Navigate between different branches:

```python
def get_owner_units(business: Business) -> list[Unit]:
    """Get units associated with the owner contact."""
    owner = business.contact_holder.owner
    if owner is None:
        return []

    # All units in same business
    return business.units

def get_active_contact_units(contact: Contact) -> list[Unit]:
    """Get active units in the contact's business."""
    business = contact.business
    if business is None:
        return []

    return [
        unit for unit in business.units
        if unit.unit_status == "Active"
    ]
```

---

## Pattern: Add New Child

Add a new entity to a holder:

```python
from uuid import uuid4

async with client.save_session() as session:
    session.track(business)
    await session.prefetch_pending()

    # Create new contact with temp GID
    new_contact = Contact(
        gid=f"temp_{uuid4()}",
        name="New Contact",
    )

    # Set parent to holder
    new_contact.parent = business.contact_holder

    # Set fields
    new_contact.full_name = "Jane Smith"
    new_contact.contact_email = "jane@example.com"
    new_contact.position = "Manager"

    # Track new entity
    session.track(new_contact)

    # Commit (creates contact as subtask of holder)
    result = await session.commit_async()

    # Get real GID from result
    real_gid = result.gid_map.get(new_contact.gid)
```

---

## Anti-Pattern: Accessing Before Prefetch

```python
# BAD: Holders not populated yet
session.track(business)
for contact in business.contacts:  # Empty list!
    print(contact.full_name)

# GOOD: Wait for prefetch
session.track(business)
await session.prefetch_pending()
for contact in business.contacts:  # Now populated
    print(contact.full_name)
```

---

## Anti-Pattern: Reusing Across Sessions

```python
# BAD: Entity reused, refs may be stale
business = await fetch_business(client, gid)

async with client.save_session() as s1:
    s1.track(business)
    await s1.commit_async()

async with client.save_session() as s2:
    s2.track(business)  # Stale refs!
    await s2.commit_async()

# GOOD: Fresh entity per session
async with client.save_session() as s1:
    b1 = await fetch_business(client, gid)
    s1.track(b1)
    await s1.commit_async()

async with client.save_session() as s2:
    b2 = await fetch_business(client, gid)  # Fresh
    s2.track(b2)
    await s2.commit_async()
```

---

## Anti-Pattern: Modifying Untracked Entity

```python
# BAD: Contact not tracked, changes lost
session.track(business)
contact = business.contacts[0]
contact.full_name = "Updated"  # Not tracked!
await session.commit_async()  # Contact not saved

# GOOD: Track what you modify
session.track(business)
contact = business.contacts[0]
session.track(contact)  # Track it
contact.full_name = "Updated"
await session.commit_async()  # Contact saved
```

---

## Pattern: Bulk Operations

Modify multiple entities efficiently:

```python
async with client.save_session() as session:
    session.track(business, recursive=True)
    await session.prefetch_pending()

    # Bulk update all contacts
    for contact in business.contacts:
        contact.campaign = "Q4-2024"

    # Bulk update all units
    for unit in business.units:
        if unit.mrr and unit.mrr < Decimal("1000"):
            unit.unit_status = "At Risk"

    # Single commit saves all
    result = await session.commit_async()
    print(f"Saved {len(result.succeeded)} entities")
```

---

## Pattern: Defensive Navigation

Handle missing references gracefully:

```python
def safe_get_business_name(contact: Contact) -> str:
    """Get business name with fallback."""
    business = contact.business
    if business is None:
        return "Unknown Business"
    return business.name or "Unnamed Business"

def safe_get_owner_email(business: Business) -> str | None:
    """Get owner email if available."""
    holder = business.contact_holder
    if holder is None:
        return None
    owner = holder.owner
    if owner is None:
        return None
    return owner.contact_email
```

---

## Related

- [holder-pattern.md](holder-pattern.md) - Holder structure
- [lazy-loading.md](lazy-loading.md) - Prefetch timing
- [bidirectional-navigation.md](bidirectional-navigation.md) - Navigation caching
