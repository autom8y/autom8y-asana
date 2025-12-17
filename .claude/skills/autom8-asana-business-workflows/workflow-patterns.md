# Workflow Patterns

> Common patterns for business entity operations

---

## Pattern: Create New Business

Create a complete business hierarchy:

```python
from uuid import uuid4

async def create_business(
    client: AsanaClient,
    project_gid: str,
    company_name: str,
    owner_name: str,
    owner_email: str,
) -> Business:
    """Create new business with owner contact."""

    async with client.save_session() as session:
        # Create business task
        business = Business(
            gid=f"temp_{uuid4()}",
            name=company_name,
        )
        business.company_name = company_name

        # Must have project
        session.add_to_project(business.gid, project_gid)
        session.track(business)

        # Create ContactHolder
        contact_holder = ContactHolder(
            gid=f"temp_{uuid4()}",
            name="Contacts",
            parent=business,
        )
        session.track(contact_holder)

        # Create owner contact
        owner = Contact(
            gid=f"temp_{uuid4()}",
            name=owner_name,
            parent=contact_holder,
        )
        owner.full_name = owner_name
        owner.contact_email = owner_email
        owner.position = "Owner"
        session.track(owner)

        # Commit
        result = await session.commit_async()

        # Update with real GIDs
        business.gid = result.gid_map.get(business.gid, business.gid)

        return business
```

---

## Pattern: Update Contact

Update an existing contact:

```python
async def update_contact(
    client: AsanaClient,
    contact_gid: str,
    **updates
) -> Contact:
    """Update contact fields."""

    async with client.save_session() as session:
        # Fetch contact
        task = await client.tasks.get(contact_gid)
        contact = Contact.model_validate(task.model_dump())

        # Track for changes
        session.track(contact)

        # Apply updates
        for field, value in updates.items():
            if hasattr(contact, field):
                setattr(contact, field, value)

        # Commit
        result = await session.commit_async()

        return contact

# Usage
contact = await update_contact(
    client,
    "123456",
    full_name="Jane Smith",
    contact_email="jane@example.com",
    position="CEO",
)
```

---

## Pattern: Add Unit to Business

Add a new unit to existing business:

```python
async def add_unit(
    client: AsanaClient,
    business_gid: str,
    vertical: str,
    mrr: Decimal,
) -> Unit:
    """Add new unit to business."""

    async with client.save_session() as session:
        # Fetch business with holders
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business)
        await session.prefetch_pending()

        # Ensure UnitHolder exists
        unit_holder = business.unit_holder
        if unit_holder is None:
            raise ValueError("Business has no UnitHolder")

        # Create new unit
        unit = Unit(
            gid=f"temp_{uuid4()}",
            name=f"{vertical} - ${mrr:,.0f}",
            parent=unit_holder,
        )
        unit.vertical = vertical
        unit.mrr = mrr
        unit.unit_status = "Active"

        session.track(unit)

        # Commit
        result = await session.commit_async()
        unit.gid = result.gid_map.get(unit.gid, unit.gid)

        return unit
```

---

## Pattern: Bulk Import Contacts

Import multiple contacts at once:

```python
async def import_contacts(
    client: AsanaClient,
    business_gid: str,
    contacts_data: list[dict],
) -> list[Contact]:
    """Bulk import contacts to business."""

    async with client.save_session() as session:
        # Fetch business
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business)
        await session.prefetch_pending()

        holder = business.contact_holder
        if holder is None:
            raise ValueError("Business has no ContactHolder")

        # Create contacts
        new_contacts = []
        for data in contacts_data:
            contact = Contact(
                gid=f"temp_{uuid4()}",
                name=data.get("full_name", "New Contact"),
                parent=holder,
            )
            contact.full_name = data.get("full_name")
            contact.contact_email = data.get("email")
            contact.contact_phone = data.get("phone")
            contact.position = data.get("position")

            session.track(contact)
            new_contacts.append(contact)

        # Commit all at once
        result = await session.commit_async()

        # Update GIDs
        for contact in new_contacts:
            contact.gid = result.gid_map.get(contact.gid, contact.gid)

        return new_contacts

# Usage
contacts = await import_contacts(client, business_gid, [
    {"full_name": "John Doe", "email": "john@example.com"},
    {"full_name": "Jane Smith", "email": "jane@example.com"},
])
```

---

## Pattern: Update All Contacts

Bulk update all contacts in a business:

```python
async def update_all_contacts(
    client: AsanaClient,
    business_gid: str,
    **common_updates
) -> int:
    """Update all contacts with common values."""

    async with client.save_session() as session:
        # Fetch business with contacts
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business, recursive=True)
        await session.prefetch_pending()

        # Update each contact
        count = 0
        for contact in business.contacts:
            for field, value in common_updates.items():
                if hasattr(contact, field):
                    setattr(contact, field, value)
            count += 1

        # Commit
        result = await session.commit_async()

        return count

# Usage
count = await update_all_contacts(
    client,
    business_gid,
    campaign="Q4-2024",
)
print(f"Updated {count} contacts")
```

---

## Pattern: Move Contact Between Businesses

Transfer contact to different business:

```python
async def move_contact(
    client: AsanaClient,
    contact_gid: str,
    target_business_gid: str,
) -> Contact:
    """Move contact to a different business."""

    async with client.save_session() as session:
        # Fetch contact
        task = await client.tasks.get(contact_gid)
        contact = Contact.model_validate(task.model_dump())
        session.track(contact)

        # Fetch target business
        target_task = await client.tasks.get(target_business_gid)
        target = Business.model_validate(target_task.model_dump())
        session.track(target)
        await session.prefetch_pending()

        target_holder = target.contact_holder
        if target_holder is None:
            raise ValueError("Target has no ContactHolder")

        # Set new parent
        contact.parent = target_holder
        contact._invalidate_refs()  # Clear cached refs

        # Commit (updates parent_task)
        result = await session.commit_async()

        return contact
```

---

## Pattern: Archive Business

Mark business and all children as completed:

```python
async def archive_business(
    client: AsanaClient,
    business_gid: str,
) -> None:
    """Archive business by completing all tasks."""

    async with client.save_session() as session:
        # Fetch full hierarchy
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business, recursive=True)
        await session.prefetch_pending()

        # Mark all as completed
        business.completed = True
        for contact in business.contacts:
            contact.completed = True
        for unit in business.units:
            unit.completed = True

        # Commit
        await session.commit_async()
```

---

## Related

- [composite-savesession.md](composite-savesession.md) - Tracking hierarchies
- [batch-operation-patterns.md](batch-operation-patterns.md) - Batch operations
- [operation-hooks.md](operation-hooks.md) - Pre/post save hooks
