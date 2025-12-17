# Workflow Patterns

> Best practices for business model workflows

---

## Entry Point Pattern

Standard workflow entry point:

```python
async def run_workflow(
    client: AsanaClient,
    **params
) -> WorkflowResult:
    """Standard workflow entry point.

    Args:
        client: Configured Asana client
        **params: Workflow-specific parameters

    Returns:
        WorkflowResult with success status and details
    """
    try:
        async with client.save_session() as session:
            # Workflow logic here
            result = await session.commit_async()
            return WorkflowResult(success=True, data=result)

    except ValidationError as e:
        return WorkflowResult(success=False, error=str(e))

    except AsanaAPIError as e:
        logger.error(f"API error: {e}")
        return WorkflowResult(success=False, error=str(e))

    except Exception as e:
        logger.exception("Workflow failed")
        return WorkflowResult(success=False, error=str(e))
```

---

## Context Manager Usage

Always use context manager:

```python
# GOOD: Context manager ensures cleanup
async with client.save_session() as session:
    session.track(business)
    await session.commit_async()

# BAD: Manual lifecycle management
session = SaveSession(client)
try:
    session.track(business)
    await session.commit_async()
finally:
    await session.close()  # Easy to forget
```

---

## Preview Before Commit

Always preview for complex operations:

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Make multiple changes
    business.company_id = "NEW"
    for contact in business.contacts:
        contact.campaign = "Q4"

    # Preview first
    ops, _ = session.preview()

    logger.info(f"Will execute {len(ops)} operations:")
    for op in ops:
        logger.info(f"  {op.operation}: {op.entity.name}")

    # Optionally confirm
    if len(ops) > 10:
        if not await confirm_large_operation(len(ops)):
            return  # Abort

    await session.commit_async()
```

---

## Error Handling Patterns

### Graceful Degradation

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Make changes
    for contact in business.contacts:
        contact.campaign = "Q4"

    result = await session.commit_async()

    if result.success:
        logger.info("All changes saved")
    else:
        # Some failed, some succeeded
        logger.warning(f"Partial success: {len(result.succeeded)} saved")
        for failed in result.failed:
            logger.error(f"Failed: {failed.entity.name}: {failed.error}")
```

### Retry Logic

```python
async def save_with_retry(
    session: SaveSession,
    max_retries: int = 3,
) -> SaveResult:
    """Save with retry on transient failures."""
    last_error = None

    for attempt in range(max_retries):
        try:
            result = await session.commit_async()
            return result
        except RateLimitError as e:
            last_error = e
            wait = e.retry_after or (2 ** attempt)
            logger.warning(f"Rate limited, waiting {wait}s")
            await asyncio.sleep(wait)
        except AsanaAPIError as e:
            if e.status_code >= 500:
                last_error = e
                await asyncio.sleep(2 ** attempt)
            else:
                raise  # Client error, don't retry

    raise last_error
```

---

## Observability

### Logging Pattern

```python
import structlog

logger = structlog.get_logger()

async with client.save_session() as session:
    log = logger.bind(workflow="update_business", business_gid=business.gid)

    log.info("Starting workflow")

    session.track(business)
    log.debug("Business tracked")

    business.company_id = new_id
    log.debug("Company ID updated", new_id=new_id)

    result = await session.commit_async()

    if result.success:
        log.info("Workflow completed", saved_count=len(result.succeeded))
    else:
        log.error("Workflow failed", failed_count=len(result.failed))
```

### Metrics

```python
from prometheus_client import Counter, Histogram

SAVE_COUNTER = Counter('business_saves_total', 'Total saves', ['status'])
SAVE_DURATION = Histogram('business_save_duration_seconds', 'Save duration')

async with client.save_session() as session:
    start = time.time()

    session.track(business)
    result = await session.commit_async()

    duration = time.time() - start
    SAVE_DURATION.observe(duration)

    if result.success:
        SAVE_COUNTER.labels(status='success').inc()
    else:
        SAVE_COUNTER.labels(status='failure').inc()
```

---

## Idempotency Pattern

Make operations safe to retry:

```python
async def idempotent_update(
    client: AsanaClient,
    contact_gid: str,
    expected_email: str,
    new_email: str,
) -> bool:
    """Update email only if current value matches expected."""
    async with client.save_session() as session:
        task = await client.tasks.get(contact_gid)
        contact = Contact.model_validate(task.model_dump())

        # Check current value
        if contact.contact_email != expected_email:
            # Already changed or different value
            return False

        # Apply update
        session.track(contact)
        contact.contact_email = new_email

        await session.commit_async()
        return True
```

---

## Transaction-like Pattern

Group related operations:

```python
async def transfer_contact(
    client: AsanaClient,
    contact_gid: str,
    source_business_gid: str,
    target_business_gid: str,
) -> None:
    """Transfer contact between businesses atomically."""
    async with client.save_session() as session:
        # Load all entities
        contact_task = await client.tasks.get(contact_gid)
        contact = Contact.model_validate(contact_task.model_dump())

        target_task = await client.tasks.get(target_business_gid)
        target = Business.model_validate(target_task.model_dump())
        session.track(target)
        await session.prefetch_pending()

        # Validate
        if not target.contact_holder:
            raise ValueError("Target has no ContactHolder")

        # Update
        session.track(contact)
        contact.parent = target.contact_holder

        # Single commit = atomic
        await session.commit_async()
```

---

## Clean Shutdown

Ensure clean shutdown:

```python
async def run_batch_workflow(client: AsanaClient, items: list):
    """Batch workflow with clean shutdown."""
    processed = 0

    try:
        for item in items:
            async with client.save_session() as session:
                await process_item(session, item)
                await session.commit_async()
                processed += 1

    except asyncio.CancelledError:
        logger.warning(f"Cancelled after {processed} items")
        raise

    finally:
        logger.info(f"Completed {processed}/{len(items)} items")
```

---

## Related

- [composite-savesession.md](composite-savesession.md) - SaveSession details
- [workflow-patterns.md](workflow-patterns.md) - Common workflows
- [batch-operation-patterns.md](batch-operation-patterns.md) - Batch operations
