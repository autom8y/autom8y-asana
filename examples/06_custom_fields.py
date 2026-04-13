"""Example: Custom Fields Management

Demonstrates:
- Creating enum custom fields (Priority, Status)
- Adding enum options with colors
- Listing custom fields in a workspace
- Setting custom field values on tasks
- Reading custom field values from tasks
- Other field types (text, number)

Requirements:
- ASANA_PAT environment variable set
- Valid workspace GID (provide via --workspace arg)
- Valid project GID for task creation (provide via --project arg)
- **Paid Asana plan** (Premium, Business, or Enterprise) - Custom fields are not available on free plans

Usage:
    export ASANA_PAT="your_token_here"
    python examples/06_custom_fields.py --workspace WORKSPACE_GID --project PROJECT_GID

Note:
    If you see a 402 Payment Required error, your Asana account does not have
    access to custom fields. This example will show what operations would be
    performed but cannot execute them without a paid plan.

Output:
    Custom field creation, task assignment, and value retrieval
"""

import asyncio
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from autom8_asana.errors import AsanaError
from _config import get_workspace_gid, get_project_gid, get_config_instructions


async def create_enum_custom_field(client: AsanaClient, workspace_gid: str) -> str:
    """Create an enum custom field with predefined options.

    Enum fields are useful for status, priority, category, etc.
    """
    print("\n=== Creating Enum Custom Field ===")

    # Define enum options (e.g., Priority levels)
    enum_options = [
        {"name": "Low", "color": "blue"},
        {"name": "Medium", "color": "yellow"},
        {"name": "High", "color": "orange"},
        {"name": "Critical", "color": "red"},
    ]

    # Create the custom field
    custom_field = await client.custom_fields.create_async(
        workspace=workspace_gid,
        name="Priority (Example)",
        resource_subtype="enum",  # Options: text, number, enum, multi_enum, date, people
        description="Task priority level",
        enum_options=enum_options,
    )

    print(f"Created custom field: {custom_field.name}")
    print(f"  GID: {custom_field.gid}")
    print(f"  Type: {custom_field.resource_subtype}")
    print("  Options:")
    if custom_field.enum_options:
        for option in custom_field.enum_options:
            print(f"    - {option.name} ({option.color})")

    return custom_field.gid


async def list_workspace_custom_fields(client: AsanaClient, workspace_gid: str) -> None:
    """List all custom fields in a workspace."""
    print("\n=== Listing Workspace Custom Fields ===")

    # List returns PageIterator - collect first 5
    custom_fields = await client.custom_fields.list_async(workspace=workspace_gid).take(
        5
    )

    print(f"Found {len(custom_fields)} custom fields (showing first 5):")
    for cf in custom_fields:
        print(f"  - {cf.name} ({cf.resource_subtype})")


async def set_custom_field_on_task(
    client: AsanaClient,
    task_gid: str,
    custom_field_gid: str,
    option_name: str,
) -> None:
    """Set a custom field value on a task.

    For enum fields, you need to find the option GID by name first.
    """
    print("\n=== Setting Custom Field on Task ===")

    # Get the custom field to find option GIDs
    custom_field = await client.custom_fields.get_async(custom_field_gid)

    # Find the option GID for "High" priority
    option_gid = None
    if custom_field.enum_options:
        for option in custom_field.enum_options:
            if option.name == option_name:
                option_gid = option.gid
                break

    if not option_gid:
        print(f"Error: Option '{option_name}' not found")
        return

    # Set the custom field value on the task
    # Custom fields are set as a dict: {custom_field_gid: value}
    updated_task = await client.tasks.update_async(
        task_gid,
        custom_fields={custom_field_gid: option_gid},
    )

    print(f"Set '{custom_field.name}' to '{option_name}' on task: {updated_task.name}")


async def read_custom_field_from_task(
    client: AsanaClient, task_gid: str, custom_field_gid: str
) -> None:
    """Read custom field values from a task."""
    print("\n=== Reading Custom Field from Task ===")

    # Get task with custom fields
    task = await client.tasks.get_async(
        task_gid,
        opt_fields=["name", "custom_fields"],
    )

    print(f"Task: {task.name}")

    # Access custom fields
    if task.custom_fields:
        for cf in task.custom_fields:
            if cf.gid == custom_field_gid:
                # For enum fields, the value is stored in enum_value
                if hasattr(cf, "enum_value") and cf.enum_value:
                    print(f"  {cf.name}: {cf.enum_value.name}")
                # For other field types
                elif hasattr(cf, "text_value") and cf.text_value:
                    print(f"  {cf.name}: {cf.text_value}")
                elif hasattr(cf, "number_value") and cf.number_value is not None:
                    print(f"  {cf.name}: {cf.number_value}")
                else:
                    print(f"  {cf.name}: (not set)")


async def demonstrate_other_field_types(
    client: AsanaClient, workspace_gid: str
) -> None:
    """Show other custom field types briefly."""
    print("\n=== Other Custom Field Types ===")

    # Text field
    print("Text field:")
    text_field = await client.custom_fields.create_async(
        workspace=workspace_gid,
        name="Notes (Example)",
        resource_subtype="text",
        description="Additional notes",
    )
    print(f"  Created: {text_field.name} ({text_field.resource_subtype})")

    # Number field
    print("\nNumber field:")
    number_field = await client.custom_fields.create_async(
        workspace=workspace_gid,
        name="Estimate Hours (Example)",
        resource_subtype="number",
        precision=2,  # 2 decimal places
    )
    print(f"  Created: {number_field.name} ({number_field.resource_subtype})")

    return text_field.gid, number_field.gid


async def cleanup_custom_fields(
    client: AsanaClient, custom_field_gids: list[str]
) -> None:
    """Clean up created custom fields."""
    print("\n=== Cleaning up custom fields ===")

    for gid in custom_field_gids:
        try:
            await client.custom_fields.delete_async(gid)
            print(f"  Deleted custom field: {gid}")
        except Exception as e:
            print(f"  Failed to delete {gid}: {e}")


async def main(workspace_gid: str, project_gid: str) -> None:
    """Run all custom fields examples."""
    print("autom8_asana SDK - Custom Fields Examples")

    created_field_gids: list[str] = []

    try:
        async with AsanaClient() as client:
            # Example 1: Create enum custom field
            priority_field_gid = await create_enum_custom_field(client, workspace_gid)
            created_field_gids.append(priority_field_gid)

            # Example 2: List workspace custom fields
            await list_workspace_custom_fields(client, workspace_gid)

            # Create a test task to demonstrate setting values
            task = await client.tasks.create_async(
                name="Custom Fields Demo Task",
                projects=[project_gid],
            )
            print(f"\nCreated test task: {task.gid}")

            # Example 3: Set custom field value on task
            await set_custom_field_on_task(client, task.gid, priority_field_gid, "High")

            # Example 4: Read custom field value from task
            await read_custom_field_from_task(client, task.gid, priority_field_gid)

            # Example 5: Other field types
            text_gid, number_gid = await demonstrate_other_field_types(
                client, workspace_gid
            )
            created_field_gids.extend([text_gid, number_gid])

            # Cleanup task
            await client.tasks.delete_async(task.gid)
            print(f"\nDeleted test task: {task.gid}")

            # Cleanup custom fields
            await cleanup_custom_fields(client, created_field_gids)

        print("\n=== Complete ===")
        print("Key Takeaways:")
        print("  - Custom fields map business concepts to Asana tasks")
        print("  - Enum fields are great for status, priority, category")
        print("  - Set values via task update: custom_fields={field_gid: value}")
        print("  - For enums, value is the option GID, not the name")
        print("  - Read values from task.custom_fields list")

    except AsanaError as e:
        if e.status_code == 402:
            print("\n" + "=" * 60)
            print("CUSTOM FIELDS REQUIRE A PAID ASANA PLAN")
            print("=" * 60)
            print("\nThis example demonstrates custom field operations, but")
            print("custom fields are only available on Asana Premium, Business,")
            print("or Enterprise plans.")
            print("\nWhat this example would demonstrate:")
            print("  1. Creating enum custom fields (like 'Priority', 'Status')")
            print("  2. Adding enum options with colors")
            print("  3. Listing custom fields in a workspace")
            print("  4. Setting custom field values on tasks")
            print("  5. Reading custom field values back")
            print("  6. Other field types (text, number, date, people)")
            print("\nTo run this example:")
            print("  - Upgrade to a paid Asana plan")
            print("  - Or use a workspace with custom fields enabled")
            print("\nSDK API calls shown in this example:")
            print("  - client.custom_fields.create_async()")
            print("  - client.custom_fields.list_async()")
            print("  - client.custom_fields.get_async()")
            print("  - client.tasks.update_async(custom_fields={...})")
            print("  - task.custom_fields (reading values)")
            print("  - client.custom_fields.delete_async()")
            print("\n" + "=" * 60)
            return
        else:
            # Re-raise other errors
            raise


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate custom fields management")
    parser.add_argument(
        "--workspace",
        default=get_workspace_gid(),
        help="Workspace GID (or set ASANA_WORKSPACE_GID env var)",
    )
    parser.add_argument(
        "--project",
        default=get_project_gid(),
        help="Project GID for test task (or set ASANA_PROJECT_GID env var)",
    )
    args = parser.parse_args()

    if not args.workspace:
        print("ERROR: No workspace GID provided")
        print(get_config_instructions())
        exit(1)

    if not args.project:
        print("ERROR: No project GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.workspace, args.project))
