#!/usr/bin/env python3
"""SDK Demonstration Suite - Main Entry Point.

Interactive demonstration suite that validates SDK operation categories
against a real Asana workspace. Uses SaveSession, action operations,
and CustomFieldAccessor with full state capture for restoration.

Per TDD-SDKDEMO: 10 demo categories with interactive confirmation.

Usage:
    python scripts/demo_sdk_operations.py [--verbose] [--category TAG|DEP|DESC|...]

Test Entity GIDs (from PRD-SDKDEMO):
    Business: 1203504488813198
    Unit: 1203504489143268
    Dependency Task: 1211596978294356
    Subtask: 1203996810236966
    Reconciliation Holder: 1203504488912317
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from autom8_asana.client import AsanaClient
from autom8_asana.models.task import Task

from _demo_utils import (
    UserAction,
    confirm,
    confirm_with_preview,
    MembershipState,
    SubtaskState,
    DemoError,
    NameResolver,
    StateManager,
    DemoLogger,
    find_custom_field_by_type,
    get_enum_option_by_index,
)


# ---------------------------------------------------------------------------
# Test Entity GIDs (Per PRD-SDKDEMO)
# ---------------------------------------------------------------------------

TEST_ENTITIES = {
    "business": "1203504488813198",
    "unit": "1203504489143268",
    "dependency_task": "1211596978294356",
    "subtask": "1203996810236966",
    "recon_holder": "1203504488912317",
}

# Default tag name for demos
DEFAULT_TAG_NAME = "optimize"


# ---------------------------------------------------------------------------
# Entity Loading
# ---------------------------------------------------------------------------


async def load_test_entities(
    client: AsanaClient,
    logger: DemoLogger,
) -> dict[str, Task]:
    """Load test entities from Asana.

    Args:
        client: SDK client.
        logger: Demo logger.

    Returns:
        Dict mapping entity names to Task objects.

    Raises:
        RuntimeError: If any required entity cannot be loaded.
    """
    logger.info("Loading test entities...")

    opt_fields = [
        "name",
        "notes",
        "html_notes",
        "completed",
        "due_on",
        "tags",
        "tags.name",
        "parent",
        "parent.name",
        "memberships",
        "memberships.project",
        "memberships.project.name",
        "memberships.section",
        "memberships.section.name",
        "custom_fields",
        "workspace",
        "workspace.name",
    ]

    entities: dict[str, Task] = {}
    failed: list[str] = []

    for name, gid in TEST_ENTITIES.items():
        try:
            task = await client.tasks.get_async(gid, opt_fields=opt_fields)
            entities[name] = task
            logger.info(f"  Loaded {name}: {task.name} ({gid})")
        except Exception as e:
            logger.warn(f"  Failed to load {name} ({gid}): {e}")
            failed.append(name)

    if failed:
        raise RuntimeError(
            f"Failed to load required entities: {', '.join(failed)}. "
            "Please verify the GIDs are correct and accessible."
        )

    return entities


async def get_workspace_gid(client: AsanaClient, entities: dict[str, Task]) -> str:
    """Extract workspace GID from loaded entities.

    Args:
        client: SDK client.
        entities: Loaded test entities.

    Returns:
        Workspace GID.

    Raises:
        RuntimeError: If workspace cannot be determined.
    """
    # Get workspace from Business entity
    business = entities.get("business")
    if business and business.workspace:
        return business.workspace.gid

    raise RuntimeError("Could not determine workspace GID from test entities")


# ---------------------------------------------------------------------------
# Demo Category: Tags (FR-TAG)
# ---------------------------------------------------------------------------


async def demo_tags(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate tag add/remove operations.

    Per FR-TAG-001..005: Add and remove tags using SaveSession.

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Tag Operations")

    # Use Business task for tag demo
    task = entities["business"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Capture initial state
    initial_snapshot = await state_manager.capture(task)
    state_manager.store_initial(task.gid, initial_snapshot)
    logger.state_capture(task.gid, initial_snapshot)
    logger.info(f"Initial tags: {[t.name for t in (task.tags or [])]}")

    # Resolve tag name to GID
    tag_gid = await resolver.resolve_tag(DEFAULT_TAG_NAME)
    logger.resolution("tag", DEFAULT_TAG_NAME, tag_gid)

    if not tag_gid:
        logger.warn(f"Tag '{DEFAULT_TAG_NAME}' not found. Creating it...")
        # Get workspace GID
        workspace_gid = await get_workspace_gid(client, entities)
        action = confirm(
            f"Create tag '{DEFAULT_TAG_NAME}' in workspace?",
            step_info="Tag not found - offer to create",
        )
        if action == UserAction.QUIT:
            logger.category_end("Tag Operations", False)
            return False
        if action == UserAction.PROCEED:
            new_tag = await client.tags.create_async(
                workspace=workspace_gid,
                name=DEFAULT_TAG_NAME,
            )
            tag_gid = new_tag.gid
            resolver.clear_cache()  # Clear cache to pick up new tag
            logger.success(f"Created tag '{DEFAULT_TAG_NAME}' ({tag_gid})")
        else:
            logger.warn("Skipping tag creation - cannot continue tag demo")
            logger.category_end("Tag Operations", False)
            return False

    # Check if tag is already on task
    current_tag_gids = [t.gid for t in (task.tags or [])]
    tag_already_present = tag_gid in current_tag_gids

    # --- Step 1: Add Tag ---
    if tag_already_present:
        logger.info(f"Tag '{DEFAULT_TAG_NAME}' is already on task - will remove first")
        # Remove tag first
        async with client.save_session() as session:
            session.remove_tag(task, tag_gid)
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Remove tag '{DEFAULT_TAG_NAME}' from task (prep for add demo)",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Tag Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.success(f"Removed tag (prep): {result}")
            else:
                logger.info("Skipped tag removal prep")

    # Now add the tag
    async with client.save_session() as session:
        session.add_tag(task, tag_gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Add tag '{DEFAULT_TAG_NAME}' to task '{task.name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Tag Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("add_tag", task.gid, {"tag_gid": tag_gid})
            logger.success(f"Added tag: {result}")
        else:
            logger.info("Skipped tag add")

    # --- Step 2: Remove Tag ---
    async with client.save_session() as session:
        session.remove_tag(task, tag_gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Remove tag '{DEFAULT_TAG_NAME}' from task '{task.name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Tag Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("remove_tag", task.gid, {"tag_gid": tag_gid})
            logger.success(f"Removed tag: {result}")
        else:
            logger.info("Skipped tag remove")

    # Update current state
    refreshed_task = await client.tasks.get_async(
        task.gid,
        opt_fields=["tags", "tags.name"],
    )
    current_snapshot = await state_manager.capture(refreshed_task)
    state_manager.store_current(task.gid, current_snapshot)

    logger.info(f"Final tags: {[t.name for t in (refreshed_task.tags or [])]}")
    logger.category_end("Tag Operations", True)
    return True


# ---------------------------------------------------------------------------
# Demo Category: Dependencies (FR-DEP)
# ---------------------------------------------------------------------------


async def demo_dependencies(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate dependency and dependent operations.

    Per FR-DEP-001..006: Add/remove dependencies and dependents using SaveSession.

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Dependency Operations")

    # Use Unit and Dependency Task
    unit_task = entities["unit"]
    dep_task = entities["dependency_task"]

    logger.info(f"Unit task: {unit_task.name} ({unit_task.gid})")
    logger.info(f"Dependency task: {dep_task.name} ({dep_task.gid})")

    # Capture initial states
    for task in [unit_task, dep_task]:
        snapshot = await state_manager.capture(task)
        state_manager.store_initial(task.gid, snapshot)
        logger.state_capture(task.gid, snapshot)

    # --- Step 1: Add Dependency (unit depends on dep_task) ---
    logger.info("\nStep 1: Add dependency (unit depends on dependency_task)")

    async with client.save_session() as session:
        session.add_dependency(unit_task, dep_task.gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Make '{unit_task.name}' depend on '{dep_task.name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Dependency Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "add_dependency", unit_task.gid, {"depends_on": dep_task.gid}
            )
            logger.success(f"Added dependency: {result}")
        else:
            logger.info("Skipped add dependency")

    # --- Step 2: Remove Dependency ---
    logger.info("\nStep 2: Remove the dependency")

    async with client.save_session() as session:
        session.remove_dependency(unit_task, dep_task.gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Remove dependency: '{unit_task.name}' no longer depends on '{dep_task.name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Dependency Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "remove_dependency", unit_task.gid, {"depends_on": dep_task.gid}
            )
            logger.success(f"Removed dependency: {result}")
        else:
            logger.info("Skipped remove dependency")

    # --- Step 3: Add Dependent (dep_task has unit as dependent) ---
    logger.info("\nStep 3: Add dependent (dependency_task blocks unit)")

    async with client.save_session() as session:
        session.add_dependent(dep_task, unit_task.gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Make '{unit_task.name}' a dependent of '{dep_task.name}' (inverse relationship)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Dependency Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "add_dependent", dep_task.gid, {"dependent": unit_task.gid}
            )
            logger.success(f"Added dependent: {result}")
        else:
            logger.info("Skipped add dependent")

    # --- Step 4: Remove Dependent ---
    logger.info("\nStep 4: Remove the dependent relationship")

    async with client.save_session() as session:
        session.remove_dependent(dep_task, unit_task.gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Remove dependent: '{unit_task.name}' no longer blocked by '{dep_task.name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Dependency Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "remove_dependent", dep_task.gid, {"dependent": unit_task.gid}
            )
            logger.success(f"Removed dependent: {result}")
        else:
            logger.info("Skipped remove dependent")

    logger.category_end("Dependency Operations", True)
    return True


# ---------------------------------------------------------------------------
# Placeholder Demos (To be implemented in Phase 2+)
# ---------------------------------------------------------------------------


async def demo_description(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate description (notes) operations.

    Per FR-DESC-001..005: Modify notes using track/commit pattern.

    Steps:
    1. Capture original notes
    2. Set new notes value
    3. Update notes to different value
    4. Clear notes
    5. Restore original value

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Description Operations")

    # Use Business task
    task = entities["business"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Capture and store initial state
    original_notes = task.notes
    logger.info(
        f"Original notes: {repr(original_notes[:100] + '...' if original_notes and len(original_notes) > 100 else original_notes)}"
    )

    # --- Step 1: Set Notes ---
    logger.info("\nStep 1: Set notes to a new value")

    test_notes_1 = "[SDK Demo] Test description - first update"

    async with client.save_session() as session:
        session.track(task)
        task.notes = test_notes_1
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Set notes to: '{test_notes_1}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Description Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("set_notes", task.gid, {"notes": test_notes_1[:50]})
            logger.success(f"Set notes: {result}")
        else:
            logger.info("Skipped set notes")

    # --- Step 2: Update Notes ---
    logger.info("\nStep 2: Update notes to different value")

    # Refresh task to get current state
    task = await client.tasks.get_async(task.gid, opt_fields=["notes"])

    test_notes_2 = "[SDK Demo] Test description - second update with more text"

    async with client.save_session() as session:
        session.track(task)
        task.notes = test_notes_2
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Update notes to: '{test_notes_2}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Description Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("update_notes", task.gid, {"notes": test_notes_2[:50]})
            logger.success(f"Updated notes: {result}")
        else:
            logger.info("Skipped update notes")

    # --- Step 3: Clear Notes ---
    logger.info("\nStep 3: Clear notes (set to empty string)")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["notes"])

    async with client.save_session() as session:
        session.track(task)
        task.notes = ""
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            "Clear notes (set to empty string)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Description Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("clear_notes", task.gid, {"notes": "(empty)"})
            logger.success(f"Cleared notes: {result}")
        else:
            logger.info("Skipped clear notes")

    # --- Step 4: Restore Original Notes ---
    logger.info("\nStep 4: Restore original notes")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["notes"])

    async with client.save_session() as session:
        session.track(task)
        task.notes = original_notes or ""
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Restore original notes: {repr(original_notes[:50] + '...' if original_notes and len(original_notes) > 50 else original_notes)}",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Description Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("restore_notes", task.gid, {"notes": "(original)"})
            logger.success(f"Restored notes: {result}")
        else:
            logger.info("Skipped restore notes")

    # Verify final state
    task = await client.tasks.get_async(task.gid, opt_fields=["notes"])
    logger.info(
        f"Final notes: {repr(task.notes[:100] + '...' if task.notes and len(task.notes) > 100 else task.notes)}"
    )

    logger.category_end("Description Operations", True)
    return True


async def demo_string_cf(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate string custom field operations.

    Per FR-CF-STR-001..005: Set/clear string custom fields.

    Steps:
    1. Find a text custom field on the task
    2. Capture original value
    3. Set to new value
    4. Update to different value
    5. Clear the field
    6. Restore original value

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("String Custom Field Operations")

    # Use Business task
    task = entities["business"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Find a text custom field
    field_info = find_custom_field_by_type(task.custom_fields, "text")
    if not field_info:
        logger.warn("No text custom field found on this task. Skipping demo.")
        logger.category_end("String Custom Field Operations", True)
        return True

    logger.info(f"Found text field: '{field_info.name}' ({field_info.gid})")
    original_value = field_info.current_value
    logger.info(f"Original value: {repr(original_value)}")

    # --- Step 1: Set Value ---
    logger.info("\nStep 1: Set string field to a new value")

    test_value_1 = "[SDK Demo] Test string value"

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, test_value_1)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Set '{field_info.name}' to: '{test_value_1}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("String Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "set_string_cf",
                task.gid,
                {"field": field_info.name, "value": test_value_1},
            )
            logger.success(f"Set string field: {result}")
        else:
            logger.info("Skipped set string field")

    # --- Step 2: Update Value ---
    logger.info("\nStep 2: Update string field to different value")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    test_value_2 = "[SDK Demo] Updated string value - more text"

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, test_value_2)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Update '{field_info.name}' to: '{test_value_2}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("String Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "update_string_cf",
                task.gid,
                {"field": field_info.name, "value": test_value_2},
            )
            logger.success(f"Updated string field: {result}")
        else:
            logger.info("Skipped update string field")

    # --- Step 3: Clear Value ---
    logger.info("\nStep 3: Clear string field (set to None)")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, None)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Clear '{field_info.name}' (set to None)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("String Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "clear_string_cf", task.gid, {"field": field_info.name, "value": None}
            )
            logger.success(f"Cleared string field: {result}")
        else:
            logger.info("Skipped clear string field")

    # --- Step 4: Restore Original Value ---
    logger.info("\nStep 4: Restore original value")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, original_value)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Restore '{field_info.name}' to original: {repr(original_value)}",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("String Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "restore_string_cf",
                task.gid,
                {"field": field_info.name, "value": "(original)"},
            )
            logger.success(f"Restored string field: {result}")
        else:
            logger.info("Skipped restore string field")

    # Verify final state
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])
    final_info = find_custom_field_by_type(task.custom_fields, "text")
    logger.info(
        f"Final value: {repr(final_info.current_value if final_info else None)}"
    )

    logger.category_end("String Custom Field Operations", True)
    return True


async def demo_people_cf(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate people custom field operations.

    Per FR-CF-PPL-001..005: Set/clear people custom fields.

    Steps:
    1. Find a people custom field on the task
    2. Capture original value
    3. Change to a different user (by name resolution)
    4. Clear the field
    5. Restore original value

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("People Custom Field Operations")

    # Use Business task
    task = entities["business"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Find a people custom field
    field_info = find_custom_field_by_type(task.custom_fields, "people")
    if not field_info:
        logger.warn("No people custom field found on this task. Skipping demo.")
        logger.category_end("People Custom Field Operations", True)
        return True

    logger.info(f"Found people field: '{field_info.name}' ({field_info.gid})")
    original_value = field_info.current_value  # List of user GIDs
    logger.info(f"Original value (user GIDs): {original_value}")

    # Pre-load users to find available users
    logger.info("Loading workspace users for demo...")
    await resolver.resolve_user("_trigger_load_")  # Force cache population
    all_users = resolver.get_all_users()

    if not all_users:
        logger.warn("Could not load users. Skipping demo.")
        logger.category_end("People Custom Field Operations", True)
        return True

    # Find a user that's different from current value
    current_user_gids = set(original_value or [])
    available_users = [
        (name, gid) for name, gid in all_users.items() if gid not in current_user_gids
    ]

    if not available_users:
        logger.warn("No alternative users available. Skipping demo.")
        logger.category_end("People Custom Field Operations", True)
        return True

    # Pick the first available user
    test_user_name, test_user_gid = available_users[0]
    logger.info(f"Will use user '{test_user_name}' ({test_user_gid}) for demo")

    # --- Step 1: Set to Different User ---
    logger.info("\nStep 1: Set people field to a different user")

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        # People fields expect a list of user GIDs
        cf.set(field_info.name, [test_user_gid])
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Set '{field_info.name}' to user: '{test_user_name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("People Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "set_people_cf",
                task.gid,
                {"field": field_info.name, "user": test_user_name},
            )
            logger.success(f"Set people field: {result}")
        else:
            logger.info("Skipped set people field")

    # --- Step 2: Clear Field ---
    logger.info("\nStep 2: Clear people field")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, None)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Clear '{field_info.name}' (set to None)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("People Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "clear_people_cf", task.gid, {"field": field_info.name, "value": None}
            )
            logger.success(f"Cleared people field: {result}")
        else:
            logger.info("Skipped clear people field")

    # --- Step 3: Restore Original Value ---
    logger.info("\nStep 3: Restore original value")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        # Restore original list of user GIDs (or None if was empty)
        restore_value = original_value if original_value else None
        cf.set(field_info.name, restore_value)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Restore '{field_info.name}' to original: {original_value}",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("People Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "restore_people_cf",
                task.gid,
                {"field": field_info.name, "value": "(original)"},
            )
            logger.success(f"Restored people field: {result}")
        else:
            logger.info("Skipped restore people field")

    # Verify final state
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])
    final_info = find_custom_field_by_type(task.custom_fields, "people")
    logger.info(f"Final value: {final_info.current_value if final_info else None}")

    logger.category_end("People Custom Field Operations", True)
    return True


async def demo_enum_cf(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate enum custom field operations.

    Per FR-CF-ENM-001..005: Set/clear enum custom fields.

    Steps:
    1. Find an enum custom field on the task
    2. Capture original value
    3. Change to a different option (by name)
    4. Clear the field
    5. Restore original value

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Enum Custom Field Operations")

    # Use Business task
    task = entities["business"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Find an enum custom field
    field_info = find_custom_field_by_type(task.custom_fields, "enum")
    if not field_info:
        logger.warn("No enum custom field found on this task. Skipping demo.")
        logger.category_end("Enum Custom Field Operations", True)
        return True

    logger.info(f"Found enum field: '{field_info.name}' ({field_info.gid})")
    original_value = field_info.current_value  # Option GID or None
    logger.info(f"Original value (option GID): {original_value}")
    logger.info(f"Display value: {field_info.display_value}")
    logger.info(
        f"Available options: {[opt['name'] for opt in field_info.enum_options]}"
    )

    # Find an option that's different from current
    new_option = get_enum_option_by_index(field_info, 0, exclude_current=True)
    if not new_option:
        # Try without exclusion if all options match current
        new_option = get_enum_option_by_index(field_info, 0, exclude_current=False)

    if not new_option:
        logger.warn("No enum options available. Skipping demo.")
        logger.category_end("Enum Custom Field Operations", True)
        return True

    new_option_gid, new_option_name = new_option
    logger.info(f"Will change to option: '{new_option_name}' ({new_option_gid})")

    # --- Step 1: Change to Different Option ---
    logger.info("\nStep 1: Change enum to different option")

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        # Enum fields expect the option GID
        cf.set(field_info.name, new_option_gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Set '{field_info.name}' to: '{new_option_name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Enum Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "set_enum_cf",
                task.gid,
                {"field": field_info.name, "option": new_option_name},
            )
            logger.success(f"Set enum field: {result}")
        else:
            logger.info("Skipped set enum field")

    # --- Step 2: Clear Field ---
    logger.info("\nStep 2: Clear enum field")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, None)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Clear '{field_info.name}' (set to None)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Enum Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "clear_enum_cf", task.gid, {"field": field_info.name, "value": None}
            )
            logger.success(f"Cleared enum field: {result}")
        else:
            logger.info("Skipped clear enum field")

    # --- Step 3: Restore Original Value ---
    logger.info("\nStep 3: Restore original value")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, original_value)
        crud_ops, action_ops = session.preview()

        # Find original option name for display
        original_name = "(None)"
        if original_value:
            for opt in field_info.enum_options:
                if opt["gid"] == original_value:
                    original_name = opt["name"]
                    break

        action = confirm_with_preview(
            f"Restore '{field_info.name}' to original: '{original_name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Enum Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "restore_enum_cf",
                task.gid,
                {"field": field_info.name, "value": "(original)"},
            )
            logger.success(f"Restored enum field: {result}")
        else:
            logger.info("Skipped restore enum field")

    # Verify final state
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])
    final_info = find_custom_field_by_type(task.custom_fields, "enum")
    logger.info(f"Final value: {final_info.display_value if final_info else None}")

    logger.category_end("Enum Custom Field Operations", True)
    return True


async def demo_number_cf(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate number custom field operations.

    Per FR-CF-NUM-001..004: Set/clear number custom fields.

    Steps:
    1. Find a number custom field on the task
    2. Capture original value
    3. Set to new value
    4. Update to different value
    5. Clear the field
    6. Restore original value

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Number Custom Field Operations")

    # Use Business task
    task = entities["business"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Find a number custom field
    field_info = find_custom_field_by_type(task.custom_fields, "number")
    if not field_info:
        logger.warn("No number custom field found on this task. Skipping demo.")
        logger.category_end("Number Custom Field Operations", True)
        return True

    logger.info(f"Found number field: '{field_info.name}' ({field_info.gid})")
    original_value = field_info.current_value
    logger.info(f"Original value: {original_value}")

    # --- Step 1: Set Value ---
    logger.info("\nStep 1: Set number field to a new value")

    test_value_1 = 12345.67

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, test_value_1)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Set '{field_info.name}' to: {test_value_1}",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Number Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "set_number_cf",
                task.gid,
                {"field": field_info.name, "value": test_value_1},
            )
            logger.success(f"Set number field: {result}")
        else:
            logger.info("Skipped set number field")

    # --- Step 2: Update Value ---
    logger.info("\nStep 2: Update number field to different value")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    test_value_2 = 99999.99

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, test_value_2)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Update '{field_info.name}' to: {test_value_2}",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Number Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "update_number_cf",
                task.gid,
                {"field": field_info.name, "value": test_value_2},
            )
            logger.success(f"Updated number field: {result}")
        else:
            logger.info("Skipped update number field")

    # --- Step 3: Clear Value ---
    logger.info("\nStep 3: Clear number field (set to None)")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, None)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Clear '{field_info.name}' (set to None)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Number Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "clear_number_cf", task.gid, {"field": field_info.name, "value": None}
            )
            logger.success(f"Cleared number field: {result}")
        else:
            logger.info("Skipped clear number field")

    # --- Step 4: Restore Original Value ---
    logger.info("\nStep 4: Restore original value")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, original_value)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Restore '{field_info.name}' to original: {original_value}",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Number Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "restore_number_cf",
                task.gid,
                {"field": field_info.name, "value": "(original)"},
            )
            logger.success(f"Restored number field: {result}")
        else:
            logger.info("Skipped restore number field")

    # Verify final state
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])
    final_info = find_custom_field_by_type(task.custom_fields, "number")
    logger.info(f"Final value: {final_info.current_value if final_info else None}")

    logger.category_end("Number Custom Field Operations", True)
    return True


async def demo_multienum_cf(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate multi-enum custom field operations.

    Per FR-CF-MEN-001..006: Set/clear/add/remove multi-enum values.

    Steps:
    1. Find a multi-enum custom field on the task
    2. Capture original values
    3. Set to single option
    4. Set to multiple options (replace all)
    5. Clear the field
    6. Restore original values

    Note: Multi-enum fields use REPLACE semantics - setting a value replaces
    all existing values, not merge/append.

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Multi-Enum Custom Field Operations")

    # Use Unit task (as per spec, multi-enum demos use Unit)
    task = entities["unit"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Find a multi-enum custom field
    field_info = find_custom_field_by_type(task.custom_fields, "multi_enum")
    if not field_info:
        logger.warn("No multi-enum custom field found on this task. Skipping demo.")
        logger.category_end("Multi-Enum Custom Field Operations", True)
        return True

    logger.info(f"Found multi-enum field: '{field_info.name}' ({field_info.gid})")
    original_value = field_info.current_value  # List of option GIDs
    logger.info(f"Original values (option GIDs): {original_value}")
    logger.info(f"Display value: {field_info.display_value}")
    logger.info(
        f"Available options: {[opt['name'] for opt in field_info.enum_options]}"
    )

    # Get at least 2 different options for the demo
    all_options = field_info.enum_options
    if len(all_options) < 2:
        logger.warn("Multi-enum field needs at least 2 options for demo. Skipping.")
        logger.category_end("Multi-Enum Custom Field Operations", True)
        return True

    # Pick options different from current (if possible)
    current_gids = set(original_value or [])
    available_options = [opt for opt in all_options if opt["gid"] not in current_gids]

    # If not enough different options, use all options
    if len(available_options) < 2:
        available_options = all_options

    option_1 = available_options[0]
    option_2 = available_options[1] if len(available_options) > 1 else all_options[1]

    logger.info(f"Demo will use options: '{option_1['name']}' and '{option_2['name']}'")

    # --- Step 1: Set Single Option ---
    logger.info("\nStep 1: Set multi-enum to single option")

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        # Multi-enum expects list of option GIDs
        cf.set(field_info.name, [option_1["gid"]])
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Set '{field_info.name}' to single option: ['{option_1['name']}']",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Multi-Enum Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "set_single_multienum",
                task.gid,
                {"field": field_info.name, "options": [option_1["name"]]},
            )
            logger.success(f"Set multi-enum to single option: {result}")
        else:
            logger.info("Skipped set single option")

    # --- Step 2: Set Multiple Options (Replace) ---
    logger.info("\nStep 2: Set multi-enum to multiple options (REPLACES previous)")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        # Replace with both options
        cf.set(field_info.name, [option_1["gid"], option_2["gid"]])
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Set '{field_info.name}' to multiple options: ['{option_1['name']}', '{option_2['name']}']",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Multi-Enum Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "set_multiple_multienum",
                task.gid,
                {
                    "field": field_info.name,
                    "options": [option_1["name"], option_2["name"]],
                },
            )
            logger.success(f"Set multi-enum to multiple options: {result}")
        else:
            logger.info("Skipped set multiple options")

    # --- Step 3: Clear Field ---
    logger.info("\nStep 3: Clear multi-enum field")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        cf.set(field_info.name, None)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Clear '{field_info.name}' (set to None)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Multi-Enum Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "clear_multienum", task.gid, {"field": field_info.name, "value": None}
            )
            logger.success(f"Cleared multi-enum field: {result}")
        else:
            logger.info("Skipped clear multi-enum field")

    # --- Step 4: Restore Original Values ---
    logger.info("\nStep 4: Restore original values")

    # Refresh task
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])

    async with client.save_session() as session:
        session.track(task)
        cf = task.custom_fields_editor()
        # Restore original list of GIDs (or None if was empty)
        restore_value = original_value if original_value else None
        cf.set(field_info.name, restore_value)
        crud_ops, action_ops = session.preview()

        # Get original option names for display
        original_names = []
        if original_value:
            gid_to_name = {opt["gid"]: opt["name"] for opt in all_options}
            original_names = [gid_to_name.get(gid, gid) for gid in original_value]

        action = confirm_with_preview(
            f"Restore '{field_info.name}' to original: {original_names or '(empty)'}",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Multi-Enum Custom Field Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "restore_multienum",
                task.gid,
                {"field": field_info.name, "value": "(original)"},
            )
            logger.success(f"Restored multi-enum field: {result}")
        else:
            logger.info("Skipped restore multi-enum field")

    # Verify final state
    task = await client.tasks.get_async(task.gid, opt_fields=["custom_fields"])
    final_info = find_custom_field_by_type(task.custom_fields, "multi_enum")
    logger.info(f"Final value: {final_info.display_value if final_info else None}")

    logger.category_end("Multi-Enum Custom Field Operations", True)
    return True


async def demo_subtask(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate subtask parent and reorder operations.

    Per FR-SUB-001..006: Set parent, reorder subtasks.

    Steps:
    1. Capture subtask's original parent and position
    2. Remove subtask from parent (set_parent to None)
    3. Add subtask back to parent
    4. Fetch siblings and reorder to bottom (insert_after last sibling)
    5. Reorder to top (insert_before first sibling)
    6. Restore original position

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Subtask Operations")

    # Use Subtask and Recon Holder (parent)
    subtask = entities["subtask"]
    recon_holder = entities["recon_holder"]

    logger.info(f"Subtask: {subtask.name} ({subtask.gid})")
    logger.info(f"Parent (Recon Holder): {recon_holder.name} ({recon_holder.gid})")

    # Capture initial parent state
    original_parent_gid = subtask.parent.gid if subtask.parent else None
    logger.info(f"Original parent GID: {original_parent_gid}")

    # Fetch siblings to capture position
    logger.info("\nFetching siblings to capture position...")
    siblings: list[Task] = []
    try:
        iterator = client.tasks.subtasks_async(
            recon_holder.gid,
            opt_fields=["name", "gid"],
        )
        async for sibling in iterator:
            siblings.append(sibling)
    except Exception as e:
        logger.warn(f"Could not fetch siblings: {e}")

    sibling_gids = [s.gid for s in siblings]
    logger.info(f"Siblings ({len(siblings)}): {[s.name for s in siblings]}")

    # Find subtask's position
    original_position = -1
    if subtask.gid in sibling_gids:
        original_position = sibling_gids.index(subtask.gid)
    logger.info(f"Original position index: {original_position}")

    # Calculate insert_after for restoration
    original_insert_after = None
    if original_position > 0:
        original_insert_after = sibling_gids[original_position - 1]
    logger.info(f"Original insert_after GID: {original_insert_after}")

    # Store subtask state
    subtask_state = SubtaskState(
        gid=subtask.gid,
        parent_gid=original_parent_gid,
        sibling_gids=sibling_gids,
        position_index=original_position,
        insert_after_gid=original_insert_after,
    )

    # --- Step 1: Remove from parent (promote to top-level) ---
    logger.info("\nStep 1: Remove subtask from parent (promote to top-level)")

    async with client.save_session() as session:
        session.set_parent(subtask, None)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Remove '{subtask.name}' from parent (promote to top-level task)",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Subtask Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("set_parent_null", subtask.gid, {"parent": None})
            logger.success(f"Removed from parent: {result}")
        else:
            logger.info("Skipped remove from parent")

    # --- Step 2: Add subtask back to parent ---
    logger.info("\nStep 2: Add subtask back to parent")

    # Refresh subtask
    subtask = await client.tasks.get_async(
        subtask.gid, opt_fields=["parent", "parent.name"]
    )

    async with client.save_session() as session:
        session.set_parent(subtask, recon_holder.gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Add '{subtask.name}' back to parent '{recon_holder.name}'",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Subtask Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation("set_parent", subtask.gid, {"parent": recon_holder.gid})
            logger.success(f"Added back to parent: {result}")
        else:
            logger.info("Skipped add to parent")

    # --- Step 3: Reorder to bottom (insert_after last sibling) ---
    logger.info("\nStep 3: Reorder subtask to bottom of siblings")

    # Refresh sibling list
    siblings = []
    try:
        iterator = client.tasks.subtasks_async(
            recon_holder.gid,
            opt_fields=["name", "gid"],
        )
        async for sibling in iterator:
            siblings.append(sibling)
    except Exception as e:
        logger.warn(f"Could not fetch siblings: {e}")

    sibling_gids = [s.gid for s in siblings]
    logger.info(f"Current siblings: {[s.name for s in siblings]}")

    # Find last sibling that's not our subtask
    last_sibling_gid = None
    for s in reversed(siblings):
        if s.gid != subtask.gid:
            last_sibling_gid = s.gid
            break

    if last_sibling_gid and len(siblings) > 1:
        # Refresh subtask with parent
        subtask = await client.tasks.get_async(
            subtask.gid, opt_fields=["parent", "parent.name", "parent.gid"]
        )

        async with client.save_session() as session:
            session.set_parent(subtask, recon_holder.gid, insert_after=last_sibling_gid)
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Move '{subtask.name}' to bottom (after last sibling)",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Subtask Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.operation(
                    "reorder_bottom", subtask.gid, {"insert_after": last_sibling_gid}
                )
                logger.success(f"Moved to bottom: {result}")
            else:
                logger.info("Skipped reorder to bottom")
    else:
        logger.info("Only one sibling - skipping reorder to bottom")

    # --- Step 4: Reorder to top (insert_before first sibling) ---
    logger.info("\nStep 4: Reorder subtask to top of siblings")

    # Refresh sibling list again
    siblings = []
    try:
        iterator = client.tasks.subtasks_async(
            recon_holder.gid,
            opt_fields=["name", "gid"],
        )
        async for sibling in iterator:
            siblings.append(sibling)
    except Exception as e:
        logger.warn(f"Could not fetch siblings: {e}")

    # Find first sibling that's not our subtask
    first_sibling_gid = None
    for s in siblings:
        if s.gid != subtask.gid:
            first_sibling_gid = s.gid
            break

    if first_sibling_gid and len(siblings) > 1:
        # Refresh subtask
        subtask = await client.tasks.get_async(
            subtask.gid, opt_fields=["parent", "parent.name", "parent.gid"]
        )

        async with client.save_session() as session:
            session.set_parent(
                subtask, recon_holder.gid, insert_before=first_sibling_gid
            )
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Move '{subtask.name}' to top (before first sibling)",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Subtask Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.operation(
                    "reorder_top", subtask.gid, {"insert_before": first_sibling_gid}
                )
                logger.success(f"Moved to top: {result}")
            else:
                logger.info("Skipped reorder to top")
    else:
        logger.info("Only one sibling - skipping reorder to top")

    # --- Step 5: Restore original position ---
    logger.info("\nStep 5: Restore original position")

    # Refresh subtask
    subtask = await client.tasks.get_async(
        subtask.gid, opt_fields=["parent", "parent.name", "parent.gid"]
    )

    if subtask_state.insert_after_gid:
        # Restore by inserting after the original predecessor
        async with client.save_session() as session:
            session.set_parent(
                subtask, recon_holder.gid, insert_after=subtask_state.insert_after_gid
            )
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Restore '{subtask.name}' to original position (after {subtask_state.insert_after_gid})",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Subtask Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.operation(
                    "restore_position",
                    subtask.gid,
                    {"insert_after": subtask_state.insert_after_gid},
                )
                logger.success(f"Restored position: {result}")
            else:
                logger.info("Skipped restore position")
    elif subtask_state.position_index == 0 and len(subtask_state.sibling_gids) > 1:
        # Was first - insert before second sibling
        second_sibling = (
            subtask_state.sibling_gids[1]
            if len(subtask_state.sibling_gids) > 1
            else None
        )
        if second_sibling:
            async with client.save_session() as session:
                session.set_parent(
                    subtask, recon_holder.gid, insert_before=second_sibling
                )
                crud_ops, action_ops = session.preview()

                action = confirm_with_preview(
                    f"Restore '{subtask.name}' to first position",
                    crud_ops,
                    action_ops,
                )

                if action == UserAction.QUIT:
                    logger.category_end("Subtask Operations", False)
                    return False
                if action == UserAction.PROCEED:
                    result = await session.commit_async()
                    logger.operation(
                        "restore_first", subtask.gid, {"insert_before": second_sibling}
                    )
                    logger.success(f"Restored to first position: {result}")
                else:
                    logger.info("Skipped restore first position")
    else:
        logger.info("No position restoration needed (was only/first sibling)")

    # Verify final state
    subtask = await client.tasks.get_async(
        subtask.gid, opt_fields=["parent", "parent.name"]
    )
    logger.info(
        f"Final parent: {subtask.parent.name if subtask.parent else '(none)'} ({subtask.parent.gid if subtask.parent else 'N/A'})"
    )

    logger.category_end("Subtask Operations", True)
    return True


async def demo_membership(
    client: AsanaClient,
    entities: dict[str, Task],
    resolver: NameResolver,
    state_manager: StateManager,
    logger: DemoLogger,
) -> bool:
    """Demonstrate project membership and section operations.

    Per FR-MEM-001..006: Add/remove from project, move to section.

    Steps:
    1. Capture original memberships (project/section)
    2. Move to different section within same project
    3. Remove from project
    4. Add back to project (in section)
    5. Add to second project (if available)
    6. Remove from second project
    7. Restore original membership

    Args:
        client: SDK client.
        entities: Loaded test entities.
        resolver: Name resolver.
        state_manager: State manager.
        logger: Demo logger.

    Returns:
        True if demo completed successfully.
    """
    logger.category_start("Project Membership Operations")

    # Use Business task
    task = entities["business"]
    logger.info(f"Using task: {task.name} ({task.gid})")

    # Capture original memberships
    original_memberships: list[MembershipState] = []
    if task.memberships:
        for m in task.memberships:
            project = m.get("project", {})
            section = m.get("section", {})
            if project.get("gid"):
                original_memberships.append(
                    MembershipState(
                        project_gid=project["gid"],
                        section_gid=section.get("gid") if section else None,
                    )
                )
                logger.info(
                    f"Original membership: project={project.get('name')} ({project.get('gid')}), section={section.get('name') if section else '(none)'}"
                )

    if not original_memberships:
        logger.warn("Task has no project memberships. Skipping demo.")
        logger.category_end("Project Membership Operations", True)
        return True

    # Use the first membership for primary operations
    primary_membership = original_memberships[0]
    primary_project_gid = primary_membership.project_gid
    original_section_gid = primary_membership.section_gid

    logger.info(f"\nPrimary project GID: {primary_project_gid}")
    logger.info(f"Original section GID: {original_section_gid}")

    # Load sections for the project
    logger.info("\nLoading sections for project...")
    sections = await resolver.get_all_sections(primary_project_gid)
    section_names = list(sections.keys())
    section_gids = list(sections.values())
    logger.info(f"Available sections ({len(sections)}): {section_names}")

    # Find a different section to move to
    target_section_gid = None
    target_section_name = None
    for name, gid in sections.items():
        if gid != original_section_gid:
            target_section_gid = gid
            target_section_name = name
            break

    # --- Step 1: Move to different section ---
    if target_section_gid:
        logger.info(f"\nStep 1: Move to different section: {target_section_name}")

        async with client.save_session() as session:
            session.move_to_section(task, target_section_gid)
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Move '{task.name}' to section '{target_section_name}'",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Project Membership Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.operation(
                    "move_to_section", task.gid, {"section": target_section_name}
                )
                logger.success(f"Moved to section: {result}")
            else:
                logger.info("Skipped move to section")
    else:
        logger.info("\nStep 1: No alternative section available - skipping")

    # --- Step 2: Remove from project ---
    logger.info("\nStep 2: Remove task from project")

    async with client.save_session() as session:
        session.remove_from_project(task, primary_project_gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Remove '{task.name}' from project",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Project Membership Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "remove_from_project", task.gid, {"project": primary_project_gid}
            )
            logger.success(f"Removed from project: {result}")
        else:
            logger.info("Skipped remove from project")

    # --- Step 3: Add back to project (in section) ---
    logger.info("\nStep 3: Add task back to project")

    # We'll add back to the original section if available
    restore_section = (
        original_section_gid
        if original_section_gid
        else (section_gids[0] if section_gids else None)
    )

    async with client.save_session() as session:
        session.add_to_project(task, primary_project_gid)
        crud_ops, action_ops = session.preview()

        action = confirm_with_preview(
            f"Add '{task.name}' back to project",
            crud_ops,
            action_ops,
        )

        if action == UserAction.QUIT:
            logger.category_end("Project Membership Operations", False)
            return False
        if action == UserAction.PROCEED:
            result = await session.commit_async()
            logger.operation(
                "add_to_project", task.gid, {"project": primary_project_gid}
            )
            logger.success(f"Added to project: {result}")
        else:
            logger.info("Skipped add to project")

    # --- Step 4: Move to original section (restore) ---
    if original_section_gid:
        logger.info("\nStep 4: Restore to original section")

        async with client.save_session() as session:
            session.move_to_section(task, original_section_gid)
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Restore '{task.name}' to original section",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Project Membership Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.operation(
                    "restore_section", task.gid, {"section": original_section_gid}
                )
                logger.success(f"Restored to original section: {result}")
            else:
                logger.info("Skipped restore to original section")
    else:
        logger.info("\nStep 4: No original section to restore to")

    # --- Step 5: Add to second project (if available) ---
    logger.info("\nStep 5: Add to a second project (demonstrating multi-project)")

    # Load all projects to find a second one
    all_projects = await resolver.get_all_projects()
    second_project_gid = None
    second_project_name = None

    # Find a project that's not the primary one
    current_project_gids = {m.project_gid for m in original_memberships}
    for name, gid in all_projects.items():
        if gid not in current_project_gids:
            second_project_gid = gid
            second_project_name = name
            break

    if second_project_gid:
        async with client.save_session() as session:
            session.add_to_project(task, second_project_gid)
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Add '{task.name}' to second project '{second_project_name}'",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Project Membership Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.operation(
                    "add_to_second_project", task.gid, {"project": second_project_name}
                )
                logger.success(f"Added to second project: {result}")
            else:
                logger.info("Skipped add to second project")

        # --- Step 6: Remove from second project ---
        logger.info("\nStep 6: Remove from second project")

        async with client.save_session() as session:
            session.remove_from_project(task, second_project_gid)
            crud_ops, action_ops = session.preview()

            action = confirm_with_preview(
                f"Remove '{task.name}' from second project '{second_project_name}'",
                crud_ops,
                action_ops,
            )

            if action == UserAction.QUIT:
                logger.category_end("Project Membership Operations", False)
                return False
            if action == UserAction.PROCEED:
                result = await session.commit_async()
                logger.operation(
                    "remove_from_second_project",
                    task.gid,
                    {"project": second_project_name},
                )
                logger.success(f"Removed from second project: {result}")
            else:
                logger.info("Skipped remove from second project")
    else:
        logger.info("No second project available - skipping multi-project demo")

    # Verify final state
    task = await client.tasks.get_async(
        task.gid,
        opt_fields=[
            "memberships",
            "memberships.project",
            "memberships.project.name",
            "memberships.section",
            "memberships.section.name",
        ],
    )
    logger.info("\nFinal memberships:")
    if task.memberships:
        for m in task.memberships:
            project = m.get("project", {})
            section = m.get("section", {})
            logger.info(
                f"  project={project.get('name')}, section={section.get('name') if section else '(none)'}"
            )
    else:
        logger.info("  (no memberships)")

    logger.category_end("Project Membership Operations", True)
    return True


# ---------------------------------------------------------------------------
# Demo Categories Registry
# ---------------------------------------------------------------------------

DEMO_CATEGORIES = {
    "TAG": ("Tag Operations", demo_tags),
    "DEP": ("Dependency Operations", demo_dependencies),
    "DESC": ("Description Operations", demo_description),
    "STR": ("String Custom Field", demo_string_cf),
    "PPL": ("People Custom Field", demo_people_cf),
    "ENM": ("Enum Custom Field", demo_enum_cf),
    "NUM": ("Number Custom Field", demo_number_cf),
    "MEN": ("Multi-Enum Custom Field", demo_multienum_cf),
    "SUB": ("Subtask Operations", demo_subtask),
    "MEM": ("Membership Operations", demo_membership),
}


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


async def run_demo(
    categories: list[str] | None = None,
    verbose: bool = False,
) -> int:
    """Run the SDK demonstration suite.

    Args:
        categories: List of category codes to run (e.g., ["TAG", "DEP"]).
                   If None, runs all categories.
        verbose: Whether to enable verbose logging.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger = DemoLogger(verbose=verbose)

    print("\n" + "=" * 60)
    print("  SDK Demonstration Suite")
    print("  Per TDD-SDKDEMO: Interactive validation of SDK operations")
    print("=" * 60)

    # Determine which categories to run
    if categories:
        selected = [
            (code, DEMO_CATEGORIES[code])
            for code in categories
            if code in DEMO_CATEGORIES
        ]
        invalid = [code for code in categories if code not in DEMO_CATEGORIES]
        if invalid:
            logger.warn(f"Unknown categories ignored: {', '.join(invalid)}")
    else:
        selected = list(DEMO_CATEGORIES.items())

    if not selected:
        logger.warn("No valid categories selected")
        return 1

    logger.info(f"Categories to run: {[name for _, (name, _) in selected]}")

    # Initialize client
    logger.info("\nInitializing SDK client...")
    try:
        client = AsanaClient()
    except Exception as e:
        logger.error(
            DemoError(
                category="initialization",
                operation="create_client",
                entity_gid="N/A",
                message=str(e),
                recovery_hint="Ensure ASANA_PAT environment variable is set",
            )
        )
        return 1

    try:
        # Load test entities
        entities = await load_test_entities(client, logger)

        # Get workspace GID
        workspace_gid = await get_workspace_gid(client, entities)
        logger.info(f"Workspace GID: {workspace_gid}")

        # Initialize utilities
        resolver = NameResolver(client, workspace_gid)
        state_manager = StateManager(client)

        # Pre-flight confirmation
        logger.info("\nTest entities loaded. Ready to begin demo.")
        action = confirm(
            "Start the demonstration?",
            step_info="This demo will make changes to test entities in Asana.",
        )

        if action != UserAction.PROCEED:
            logger.info("Demo cancelled by user")
            return 0

        # Run selected categories
        results: dict[str, bool] = {}
        for code, (name, func) in selected:
            logger.info(f"\n--- Running: {name} ({code}) ---")

            try:
                success = await func(client, entities, resolver, state_manager, logger)
                results[code] = success
            except Exception as e:
                logger.error(
                    DemoError(
                        category=code,
                        operation="run_category",
                        entity_gid="N/A",
                        message=str(e),
                    )
                )
                results[code] = False

            # Check if user wants to continue
            if not success:
                action = confirm(
                    "Continue with remaining categories?",
                    step_info=f"Category {code} did not complete successfully.",
                )
                if action == UserAction.QUIT:
                    logger.info("Demo stopped by user")
                    break

        # Summary
        print("\n" + "=" * 60)
        print("  Demo Summary")
        print("=" * 60)
        for code, success in results.items():
            name = DEMO_CATEGORIES[code][0]
            status = "PASS" if success else "FAIL"
            print(f"  [{status}] {name}")

        passed = sum(1 for s in results.values() if s)
        total = len(results)
        print(f"\n  {passed}/{total} categories completed successfully")
        print("=" * 60)

        return 0 if passed == total else 1

    finally:
        await client.close()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SDK Demonstration Suite - Interactive validation of SDK operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Category codes:
  TAG  - Tag add/remove operations
  DEP  - Dependency and dependent operations
  DESC - Description (notes) modifications
  STR  - String custom field operations
  PPL  - People custom field operations
  ENM  - Enum custom field operations
  NUM  - Number custom field operations
  MEN  - Multi-enum custom field operations
  SUB  - Subtask parent and reorder operations
  MEM  - Project membership and section operations

Examples:
  python demo_sdk_operations.py                    # Run all categories
  python demo_sdk_operations.py --category TAG     # Run only tag demo
  python demo_sdk_operations.py -c TAG -c DEP      # Run tag and dependency demos
  python demo_sdk_operations.py --verbose          # Run with verbose logging
""",
    )
    parser.add_argument(
        "-c",
        "--category",
        action="append",
        dest="categories",
        choices=list(DEMO_CATEGORIES.keys()),
        help="Category code to run (can be specified multiple times)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(
        run_demo(
            categories=args.categories,
            verbose=args.verbose,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
