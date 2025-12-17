# Operation Hooks

> Pre-save validation and post-save callbacks

---

## Hook Pattern Overview

SaveSession supports hooks at key lifecycle points:

```python
async with client.save_session() as session:
    # Register hooks
    session.on_pre_save(validate_business)
    session.on_post_save(log_changes)

    session.track(business)
    business.company_id = "NEW"

    # Hooks fire during commit
    await session.commit_async()
```

---

## Pre-Save Hooks

Validate before saving:

```python
from typing import Callable, Awaitable

PreSaveHook = Callable[[list[PlannedOperation]], Awaitable[None]]

def validate_business(operations: list[PlannedOperation]) -> None:
    """Validate business operations before save."""
    for op in operations:
        if isinstance(op.entity, Business):
            if not op.entity.company_id:
                raise ValueError("Business must have company_id")

def validate_contact_has_email(operations: list[PlannedOperation]) -> None:
    """Ensure contacts have email addresses."""
    for op in operations:
        if isinstance(op.entity, Contact):
            if not op.entity.contact_email:
                raise ValueError(f"Contact {op.entity.name} needs email")

# Register hooks
session.on_pre_save(validate_business)
session.on_pre_save(validate_contact_has_email)
```

---

## Async Pre-Save Hooks

Hooks can be async for external validation:

```python
async def validate_unique_company_id(operations: list[PlannedOperation]) -> None:
    """Check company_id uniqueness against database."""
    for op in operations:
        if isinstance(op.entity, Business):
            company_id = op.entity.company_id
            if company_id and await db.exists_company(company_id):
                raise ValueError(f"Company ID {company_id} already exists")

# Register async hook
session.on_pre_save(validate_unique_company_id)
```

---

## Post-Save Hooks

React after successful save:

```python
PostSaveHook = Callable[[SaveResult], Awaitable[None]]

async def log_changes(result: SaveResult) -> None:
    """Log successful saves."""
    for entity in result.succeeded:
        logger.info(f"Saved: {entity.gid} - {entity.name}")

async def notify_slack(result: SaveResult) -> None:
    """Send Slack notification for new businesses."""
    for entity in result.succeeded:
        if isinstance(entity, Business):
            await slack.post(f"New business created: {entity.name}")

async def update_cache(result: SaveResult) -> None:
    """Update local cache after save."""
    for entity in result.succeeded:
        cache.set(entity.gid, entity)

# Register post-save hooks
session.on_post_save(log_changes)
session.on_post_save(notify_slack)
session.on_post_save(update_cache)
```

---

## Business Validation Hooks

Common business rule validations:

```python
def validate_owner_contact(operations: list[PlannedOperation]) -> None:
    """Ensure business has owner contact."""
    businesses = [
        op.entity for op in operations
        if isinstance(op.entity, Business)
    ]

    for business in businesses:
        if business.contact_holder:
            if not business.contact_holder.owner:
                raise ValueError(f"Business {business.name} needs owner contact")

def validate_unit_has_vertical(operations: list[PlannedOperation]) -> None:
    """Units must have vertical set."""
    for op in operations:
        if isinstance(op.entity, Unit):
            if not op.entity.vertical:
                raise ValueError(f"Unit {op.entity.name} needs vertical")

def validate_mrr_positive(operations: list[PlannedOperation]) -> None:
    """MRR must be positive."""
    for op in operations:
        if isinstance(op.entity, Unit):
            mrr = op.entity.mrr
            if mrr is not None and mrr < 0:
                raise ValueError(f"Unit {op.entity.name} has negative MRR")
```

---

## Conditional Hooks

Apply hooks based on context:

```python
def create_validation_hook(strict: bool = False):
    """Factory for validation hooks with strictness setting."""

    def validate(operations: list[PlannedOperation]) -> None:
        for op in operations:
            if isinstance(op.entity, Contact):
                # Always require name
                if not op.entity.full_name:
                    raise ValueError("Contact needs full_name")

                # In strict mode, require email too
                if strict and not op.entity.contact_email:
                    raise ValueError("Contact needs email (strict mode)")

    return validate

# Use appropriate strictness
if production:
    session.on_pre_save(create_validation_hook(strict=True))
else:
    session.on_pre_save(create_validation_hook(strict=False))
```

---

## Hook Registration Pattern

```python
class SaveSession:
    def __init__(self):
        self._pre_save_hooks: list[PreSaveHook] = []
        self._post_save_hooks: list[PostSaveHook] = []

    def on_pre_save(self, hook: PreSaveHook) -> None:
        """Register pre-save validation hook."""
        self._pre_save_hooks.append(hook)

    def on_post_save(self, hook: PostSaveHook) -> None:
        """Register post-save callback hook."""
        self._post_save_hooks.append(hook)

    async def commit_async(self) -> SaveResult:
        # Get operations
        operations = self.preview()

        # Run pre-save hooks
        for hook in self._pre_save_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook(operations)
            else:
                hook(operations)

        # Execute saves
        result = await self._execute_saves(operations)

        # Run post-save hooks
        for hook in self._post_save_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook(result)
            else:
                hook(result)

        return result
```

---

## Error Hook

Handle save failures:

```python
ErrorHook = Callable[[Exception, list[PlannedOperation]], Awaitable[None]]

async def on_save_error(error: Exception, operations: list[PlannedOperation]) -> None:
    """Handle save errors."""
    logger.error(f"Save failed: {error}")

    # Log what was being saved
    for op in operations:
        logger.error(f"  Pending: {op.operation} {op.entity.gid}")

    # Notify
    await alert.send(f"Save failed: {error}")

session.on_error(on_save_error)
```

---

## Composable Validators

Build complex validation from simple parts:

```python
def compose_validators(*validators):
    """Combine multiple validators into one hook."""
    def combined(operations: list[PlannedOperation]) -> None:
        for validator in validators:
            validator(operations)
    return combined

# Combine validators
business_validator = compose_validators(
    validate_company_id_present,
    validate_owner_contact,
    validate_mrr_positive,
)

session.on_pre_save(business_validator)
```

---

## Related

- [composite-savesession.md](composite-savesession.md) - SaveSession details
- [workflow-patterns.md](workflow-patterns.md) - Common workflows
- [patterns-workflows.md](patterns-workflows.md) - Best practices
