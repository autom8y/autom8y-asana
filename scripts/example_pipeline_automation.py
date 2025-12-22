#!/usr/bin/env python3
"""Pipeline Automation Demo: Sales -> Onboarding Conversion.

Demonstrates the Automation Layer capabilities:
1. AutomationEngine with rule registration
2. PipelineConversionRule triggers on section_changed
3. TemplateDiscovery finds template tasks
4. Automatic task creation in target project
5. AutomationResult with execution details
6. WorkspaceProjectRegistry for dynamic pipeline project discovery

This script shows how to configure pipeline automation that triggers
when a Sales Process is moved to the "Converted" section, automatically
creating a new Onboarding Process in the target project.

The WorkspaceProjectRegistry enables automatic discovery of pipeline
projects (Sales, Onboarding, etc.) without requiring hardcoded GIDs
in the configuration.

Usage:
    export ASANA_PAT='your_personal_access_token'
    export ASANA_WORKSPACE_GID='your_workspace_gid'
    python scripts/example_pipeline_automation.py

    # With specific Process GID:
    python scripts/example_pipeline_automation.py --gid 1209719836385072

    # Dry run (shows what would happen without committing):
    python scripts/example_pipeline_automation.py --dry-run

    # Discover projects and show what's available:
    python scripts/example_pipeline_automation.py --discover-only

Known Limitations (Deferred to Phase 2):
    - Field seeding: Custom fields are not yet copied to the created task
    - Subtask copying: Template subtasks are not yet duplicated

Note:
    The demo may show an error if the target Onboarding project doesn't
    have a "Template" section. This is expected behavior - the rule fails
    gracefully with a clear error message.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

from autom8_asana.automation import (
    AutomationConfig,
    PipelineConversionRule,
    PipelineStage,
)
from autom8_asana.automation.pipeline import ProcessSection, ProcessType
from autom8_asana.client import AsanaClient
from autom8_asana.config import AsanaConfig
from autom8_asana.models.business import Process, hydrate_from_gid_async
from autom8_asana.models.business.registry import get_workspace_registry
from autom8_asana.persistence import SaveSession
from autom8_asana.persistence.models import AutomationResult


# =============================================================================
# Display Helpers
# =============================================================================


def format_value(value: Any, default: str = "(not set)") -> str:
    """Format a value for display, handling None and empty values.

    Args:
        value: Value to format.
        default: Default string for None/empty values.

    Returns:
        Formatted string representation.
    """
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else default
    return str(value)


def print_section(title: str, char: str = "-", width: int = 70) -> None:
    """Print a section header.

    Args:
        title: Section title text.
        char: Character to use for the border.
        width: Width of the border line.
    """
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_field(label: str, value: Any, indent: int = 4) -> None:
    """Print a field with proper indentation and formatting.

    Args:
        label: Field label.
        value: Field value.
        indent: Number of spaces to indent.
    """
    prefix = " " * indent
    print(f"{prefix}{label}: {format_value(value)}")


def print_automation_result(result: AutomationResult, indent: int = 4) -> None:
    """Print detailed AutomationResult information.

    Args:
        result: The AutomationResult to display.
        indent: Number of spaces to indent.
    """
    prefix = " " * indent
    status_icon = "[OK]" if result.success else "[FAILED]"
    if result.was_skipped:
        status_icon = "[SKIPPED]"

    print(f"\n{prefix}{status_icon} {result.rule_name}")
    print(f"{prefix}    Rule ID: {result.rule_id}")
    print(
        f"{prefix}    Triggered By: {result.triggered_by_type} ({result.triggered_by_gid})"
    )

    if result.actions_executed:
        print(f"{prefix}    Actions Executed: {', '.join(result.actions_executed)}")

    if result.entities_created:
        print(f"{prefix}    Entities Created: {', '.join(result.entities_created)}")

    if result.entities_updated:
        print(f"{prefix}    Entities Updated: {', '.join(result.entities_updated)}")

    if result.execution_time_ms > 0:
        print(f"{prefix}    Execution Time: {result.execution_time_ms:.2f}ms")

    if result.error:
        print(f"{prefix}    Error: {result.error}")

    if result.skipped_reason:
        print(f"{prefix}    Skipped Reason: {result.skipped_reason}")


# =============================================================================
# Workspace Discovery
# =============================================================================


async def discover_workspace_projects(client: AsanaClient) -> dict[str, str]:
    """Discover all projects in the workspace and identify pipeline projects.

    Per TDD-WORKSPACE-PROJECT-REGISTRY: Lazy discovery via WorkspaceProjectRegistry.

    This function demonstrates the dynamic project discovery capability.
    After discovery, pipeline projects are automatically registered for
    entity type detection.

    Args:
        client: AsanaClient with default_workspace_gid set.

    Returns:
        Dict mapping ProcessType values to project GIDs.

    Example:
        >>> pipeline_gids = await discover_workspace_projects(client)
        >>> print(pipeline_gids)
        {'sales': '123...', 'onboarding': '456...'}
    """
    registry = get_workspace_registry()

    # Trigger discovery
    await registry.discover_async(client)

    # Collect discovered pipeline projects
    pipeline_gids: dict[str, str] = {}
    for name, gid in registry._name_to_gid.items():
        process_type = registry.get_process_type(gid)
        if process_type is not None:
            pipeline_gids[process_type.value] = gid

    return pipeline_gids


async def demo_discover_projects_only(client: AsanaClient) -> int:
    """Demonstrate workspace project discovery.

    Shows all discovered projects and identifies pipeline projects.

    Args:
        client: AsanaClient with default_workspace_gid set.

    Returns:
        Exit code (0 = success).
    """
    print("\n" + "=" * 70)
    print("  WorkspaceProjectRegistry - Pipeline Discovery Demo")
    print("=" * 70)

    print(f"\n  Workspace GID: {client.default_workspace_gid}")
    print("\n  Discovering all projects in workspace...")

    registry = get_workspace_registry()
    await registry.discover_async(client)

    print(f"\n  Discovered {len(registry._name_to_gid)} projects")

    # Show pipeline projects
    print_section("PIPELINE PROJECTS DISCOVERED")

    pipeline_count = 0
    for name, gid in sorted(registry._name_to_gid.items()):
        process_type = registry.get_process_type(gid)
        if process_type is not None:
            pipeline_count += 1
            print(f"    [{process_type.value.upper()}] {name}")
            print_field("GID", gid, indent=8)
            print()

    if pipeline_count == 0:
        print("    (No pipeline projects found)")
        print()
        print("    Pipeline projects are identified by name containing:")
        print("    - sales, outreach, onboarding, implementation")
        print("    - retention, reactivation")

    # Show how to use for automation
    print_section("USING DISCOVERED PROJECTS FOR AUTOMATION")
    print()
    print("  With WorkspaceProjectRegistry, you no longer need to hardcode")
    print("  pipeline project GIDs. Entity detection works transparently:")
    print()
    print("    # Detection automatically discovers pipeline projects")
    print("    result = await detect_entity_type_async(task, client)")
    print("    if result.entity_type == EntityType.PROCESS:")
    print('        print(f"Detected Process via Tier 1 discovery")')
    print()
    print("  For automation config, get GIDs by project name:")
    print()
    print("    registry = get_workspace_registry()")
    print('    sales_gid = registry.get_by_name("Sales Pipeline")')
    print('    onboarding_gid = registry.get_by_name("Onboarding")')

    print("\n" + "=" * 70)
    print("  Discovery Complete!")
    print("=" * 70)

    return 0


# =============================================================================
# Demo Implementation
# =============================================================================


async def demo_pipeline_automation(
    process_gid: str,
    onboarding_project_gid: str | None,
    workspace_gid: str,
    dry_run: bool = False,
    use_discovery: bool = True,
) -> int:
    """Demonstrate pipeline automation from Sales to Onboarding.

    This demo shows the complete automation flow:
    1. Create an AsanaClient with AutomationConfig
    2. Optionally discover workspace projects via WorkspaceProjectRegistry
    3. Register PipelineConversionRule with the automation engine
    4. Load a Sales Process and display its current state
    5. List available sections in the Sales project
    6. Move the Process to the "Converted" section
    7. Display the AutomationResult showing what happened

    Args:
        process_gid: GID of the Sales Process to work with.
        onboarding_project_gid: GID of the target Onboarding project.
                               If None and use_discovery=True, will attempt
                               to discover from workspace.
        workspace_gid: GID of the Asana workspace to use.
        dry_run: If True, show the preview without committing.
        use_discovery: If True, use WorkspaceProjectRegistry to discover
                      pipeline projects dynamically.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    print("\n" + "=" * 70)
    print("  autom8_asana SDK - Pipeline Automation Demo")
    print("=" * 70)
    print(f"\n  Process GID: {process_gid}")
    print(f"  Onboarding Project GID: {format_value(onboarding_project_gid)}")
    print(f"  Mode: {'Dry Run (preview only)' if dry_run else 'Live (will commit)'}")
    print(f"  Discovery Mode: {'Enabled' if use_discovery else 'Disabled'}")

    # =========================================================================
    # SECTION 1: CLIENT CONFIGURATION WITH AUTOMATION
    # =========================================================================
    print_section("1. CLIENT CONFIGURATION WITH AUTOMATION", "=")

    print("\n  Creating AsanaClient with AutomationConfig...")
    print("  The AutomationConfig enables the automation engine and specifies")
    print("  pipeline templates that map process types to target projects.")

    # Build initial AutomationConfig
    # Using pipeline_stages (preferred) instead of pipeline_templates (legacy)
    # When use_discovery=True, we'll update pipeline_stages after discovery
    automation_config = AutomationConfig(
        enabled=True,
        max_cascade_depth=5,  # Prevent infinite automation loops
        pipeline_stages={
            # Map ProcessType.ONBOARDING to the target project with full config
            # Will be populated from discovery if onboarding_project_gid is None
            "onboarding": PipelineStage(
                project_gid=onboarding_project_gid or "",
                target_section="Opportunity",
                due_date_offset_days=7,
                business_cascade_fields=[
                    "Office Phone",
                ],
                unit_cascade_fields=[
                    "Vertical",
                    "Products",
                    "MRR",
                    "Rep",
                    "Platforms",
                    "Booking Type",
                ],
                process_carry_through_fields=[
                    "Contact Phone",
                    "Priority",
                ],
                field_name_mapping={},
            ),
        },
    )

    # Create the full AsanaConfig with automation settings
    config = AsanaConfig(automation=automation_config)

    print("\n  AutomationConfig:")
    print_field("enabled", automation_config.enabled)
    print_field("max_cascade_depth", automation_config.max_cascade_depth)
    # Show pipeline_stages (preferred config)
    if automation_config.pipeline_stages:
        print("    pipeline_stages:")
        for name, stage in automation_config.pipeline_stages.items():
            print(f"      {name}:")
            print_field("project_gid", stage.project_gid, indent=8)
            print_field("target_section", stage.target_section, indent=8)
            print_field("due_date_offset_days", stage.due_date_offset_days, indent=8)
            print_field("assignee_gid", stage.assignee_gid, indent=8)

    async with AsanaClient(config=config, workspace_gid=workspace_gid) as client:
        # =====================================================================
        # SECTION 1.5: WORKSPACE PROJECT DISCOVERY (Optional)
        # =====================================================================
        if use_discovery:
            print_section("1.5. WORKSPACE PROJECT DISCOVERY", "=")

            print("\n  Using WorkspaceProjectRegistry to discover pipeline projects...")
            print("  This eliminates the need for hardcoded project GIDs.")

            # Discover workspace projects
            registry = get_workspace_registry()
            await registry.discover_async(client)

            # Show discovered pipeline projects
            pipeline_count = 0
            discovered_onboarding_gid: str | None = None

            print("\n  Pipeline projects found:")
            for name, gid in sorted(registry._name_to_gid.items()):
                process_type = registry.get_process_type(gid)
                if process_type is not None:
                    pipeline_count += 1
                    print(f"    - {name} [{process_type.value.upper()}] ({gid})")
                    if process_type == ProcessType.ONBOARDING:
                        discovered_onboarding_gid = gid

            if pipeline_count == 0:
                print("    (No pipeline projects found in workspace)")

            # Update automation config if we discovered an onboarding project
            if discovered_onboarding_gid and not onboarding_project_gid:
                print(f"\n  Discovered Onboarding project: {discovered_onboarding_gid}")
                print("  Updating AutomationConfig with discovered GID...")
                # Update the PipelineStage with discovered project GID
                automation_config.pipeline_stages["onboarding"] = PipelineStage(
                    project_gid=discovered_onboarding_gid,
                    target_section="Opportunity",
                    due_date_offset_days=7,
                    business_cascade_fields=[
                        "Office Phone",
                    ],
                    unit_cascade_fields=[
                        "Vertical",
                        "Products",
                        "MRR",
                        "Rep",
                        "Platforms",
                        "Booking Type",
                    ],
                    process_carry_through_fields=[
                        "Contact Phone",
                        "Priority",
                    ],
                    field_name_mapping={},
                )

        # =====================================================================
        # SECTION 2: REGISTER PIPELINE CONVERSION RULE
        # =====================================================================
        print_section("2. REGISTER PIPELINE CONVERSION RULE", "=")

        print("\n  The PipelineConversionRule is a built-in automation rule that:")
        print("    - Triggers when a Process moves to a specific section")
        print("    - Creates a new Process in the target project")
        print("    - Copies relevant fields from the source process")

        # Create the rule with default Sales -> Onboarding conversion
        rule = PipelineConversionRule(
            source_type=ProcessType.SALES,
            target_type=ProcessType.ONBOARDING,
            trigger_section=ProcessSection.CONVERTED,
        )

        print("\n  PipelineConversionRule Configuration:")
        print_field("Rule ID", rule.id)
        print_field("Rule Name", rule.name)
        print_field("Source Type", rule._source_type.value)
        print_field("Target Type", rule._target_type.value)
        print_field("Trigger Section", rule._trigger_section.value)

        # Register the rule with the automation engine
        if client.automation:
            client.automation.register(rule)
            print("\n  Rule registered successfully with AutomationEngine")
            print(f"  Total registered rules: {len(client.automation.rules)}")
        else:
            print("\n  WARNING: Automation engine not available")
            print("  (automation.enabled may be False in config)")

        # =====================================================================
        # SECTION 3: LOAD AND INSPECT PROCESS
        # =====================================================================
        print_section("3. LOAD AND INSPECT PROCESS", "=")

        print(f"\n  Hydrating hierarchy from Process GID: {process_gid}...")

        # Hydrate the full business hierarchy from the Process
        result = await hydrate_from_gid_async(client, process_gid)

        if not result.business:
            print(f"\n  ERROR: Could not hydrate hierarchy from GID {process_gid}")
            print(f"  Entry type detected: {result.entry_type}")
            return 1

        print("\n  Hydration Result:")
        print_field("Business", result.business.name)
        print_field(
            "Entry Type", result.entry_type.value if result.entry_type else "Business"
        )
        print_field("API Calls", result.api_calls)
        print_field("Complete", result.is_complete)

        # Find the Process in the hydrated hierarchy
        process: Process | None = None
        for unit in result.business.units:
            for proc in unit.processes:
                if proc.gid == process_gid:
                    process = proc
                    break
            if process:
                break

        if not process:
            print(f"\n  ERROR: Process {process_gid} not found in hierarchy")
            print("  The GID may not be a Process task, or it may not be")
            print("  connected to the Business hierarchy.")
            return 1

        print("\n  Process Found:")
        print_field("Name", process.name)
        print_field("GID", process.gid)
        print_field("Process Type", process.process_type.value)
        print_field(
            "Pipeline State",
            process.pipeline_state.value if process.pipeline_state else None,
        )
        print_field("Status", process.status)
        print_field("Priority", process.priority)

        # Show hierarchy navigation
        print("\n  Hierarchy Navigation:")
        if process.unit:
            print_field("Unit", process.unit.name)
        if process.business:
            print_field("Business", process.business.name)

        # =====================================================================
        # SECTION 4: FIND SECTIONS IN SALES PROJECT
        # =====================================================================
        print_section("4. FIND SECTIONS IN SALES PROJECT", "=")

        print("\n  To move the Process to 'Converted', we need to:")
        print("    1. Find the project the Process belongs to")
        print("    2. List sections in that project")
        print("    3. Find the 'Converted' section")

        # Get project from Process memberships
        project_gid: str | None = None
        if process.memberships:
            for membership in process.memberships:
                project_info = membership.get("project", {})
                if project_info.get("gid"):
                    project_gid = project_info["gid"]
                    project_name = project_info.get("name", "(unknown)")
                    print(f"\n  Process belongs to project: {project_name}")
                    print_field("Project GID", project_gid)
                    break

        if not project_gid:
            print("\n  ERROR: Could not determine project for this Process")
            print("  The Process may not be in any project.")
            return 1

        # List sections in the project
        print(f"\n  Listing sections in project {project_gid}...")
        sections = await client.sections.list_for_project_async(project_gid).collect()

        print(f"\n  Found {len(sections)} sections:")
        converted_section = None
        for section in sections:
            marker = ""
            section_enum = ProcessSection.from_name(section.name)
            if section_enum == ProcessSection.CONVERTED:
                converted_section = section
                marker = " <-- TARGET"
            print(f"    - {section.name} ({section.gid}){marker}")

        if not converted_section:
            print("\n  WARNING: No 'Converted' section found in the project")
            print("  Creating a section named 'Converted' would be required.")
            print("  For this demo, we'll continue to show the automation flow.")

        # =====================================================================
        # SECTION 5: MOVE PROCESS TO CONVERTED SECTION
        # =====================================================================
        print_section("5. MOVE PROCESS TO CONVERTED SECTION", "=")

        if not converted_section:
            print("\n  SKIPPED: No Converted section available")
            print("  In a real scenario, you would create the section first.")
            return 0

        print(f"\n  Moving Process to section: {converted_section.name}")
        print(f"  Section GID: {converted_section.gid}")

        # Create a SaveSession with automation enabled
        # The automation will run after the commit completes
        async with SaveSession(
            client,
            automation_enabled=True,
        ) as session:
            # Track the Process (required for SaveSession operations)
            session.track(process)

            # Queue the move_to_section action
            # This will trigger the "section_changed" event after commit
            session.move_to_section(process, converted_section)

            if dry_run:
                # Preview mode - show what would happen
                print("\n  DRY RUN - Previewing operations:")
                crud_ops, action_ops = session.preview()

                print(f"\n  CRUD Operations: {len(crud_ops)}")
                for op in crud_ops:
                    print(f"    - {op.operation.value}: {op.entity.gid}")

                print(f"\n  Action Operations: {len(action_ops)}")
                for action in action_ops:
                    target_gid = action.target.gid if action.target else None
                    print(
                        f"    - {action.action.value}: {action.task.gid} -> {target_gid}"
                    )

                print("\n  NOTE: No changes committed (dry run mode)")
                print("  Run without --dry-run to execute the automation.")
                return 0

            # Commit the changes - this triggers automation
            print("\n  Committing changes and triggering automation...")
            save_result = await session.commit_async()

        # =====================================================================
        # SECTION 6: DISPLAY AUTOMATION RESULTS
        # =====================================================================
        print_section("6. AUTOMATION RESULTS", "=")

        print("\n  SaveResult Summary:")
        print_field("CRUD Succeeded", len(save_result.succeeded))
        print_field("CRUD Failed", len(save_result.failed))
        print_field("Actions Executed", len(save_result.action_results))
        print_field("Automation Rules", len(save_result.automation_results))

        # Show action results
        if save_result.action_results:
            print("\n  Action Results:")
            for action_result in save_result.action_results:
                status = "[OK]" if action_result.success else "[FAILED]"
                target = action_result.action.target
                target_str = target.gid if target else "(none)"
                print(f"    {status} {action_result.action.action.value}: {target_str}")
                if action_result.error:
                    print(f"         Error: {action_result.error}")

        # Show automation results - the main focus of this demo
        if save_result.automation_results:
            print("\n  Automation Results:")
            for auto_result in save_result.automation_results:
                print_automation_result(auto_result)
        else:
            print("\n  No automation rules were triggered.")
            print("  This could mean:")
            print("    - The Process is not a SALES type")
            print("    - The section is not 'Converted'")
            print("    - No rules matched the event")

        # =====================================================================
        # SECTION 7: SUMMARY
        # =====================================================================
        print_section("7. SUMMARY", "=")

        # Determine overall success
        automation_succeeded = sum(
            1 for r in save_result.automation_results if r.success and not r.was_skipped
        )
        automation_failed = sum(
            1 for r in save_result.automation_results if not r.success
        )

        print("\n  Pipeline Automation Demo Complete!")
        print("\n  What Happened:")
        print("    1. Created AsanaClient with AutomationConfig")
        print("    2. Registered PipelineConversionRule (Sales -> Onboarding)")
        print(f"    3. Loaded Process: {process.name}")
        print(f"    4. Moved to section: {converted_section.name}")
        print(
            f"    5. Automation triggered: {automation_succeeded} succeeded, {automation_failed} failed"
        )

        if automation_failed > 0:
            print("\n  Note: Some automation rules failed. Common reasons:")
            print("    - Target project has no 'Template' section")
            print("    - Template task not found in target project")
            print("    - Network or permission errors")

        # Check for created entities
        for auto_result in save_result.automation_results:
            if auto_result.entities_created:
                print("\n  NEW ENTITIES CREATED:")
                for gid in auto_result.entities_created:
                    print(f"    - {gid}")

        print("\n" + "=" * 70)
        print("  Demo Complete!")
        print("=" * 70)

        return 0


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> None:
    """CLI entry point for the pipeline automation demo."""
    parser = argparse.ArgumentParser(
        description="Demonstrate Sales -> Onboarding pipeline automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use default Process GID with automatic project discovery
    python scripts/example_pipeline_automation.py

    # Use specific Process GID
    python scripts/example_pipeline_automation.py --gid 1209719836385072

    # Preview without committing
    python scripts/example_pipeline_automation.py --dry-run

    # Discover projects only (no automation)
    python scripts/example_pipeline_automation.py --discover-only

    # Specify target Onboarding project (skip discovery)
    python scripts/example_pipeline_automation.py --onboarding-project 1234567890

    # Disable automatic discovery
    python scripts/example_pipeline_automation.py --no-discovery

Automation Flow:
    1. Discover workspace projects via WorkspaceProjectRegistry
    2. Configure AutomationConfig with discovered pipeline_templates
    3. Register PipelineConversionRule with AutomationEngine
    4. Load Process and move to "Converted" section
    5. SaveSession.commit_async() triggers automation
    6. AutomationResult shows created entities and execution details

Environment:
    ASANA_PAT: Your Asana Personal Access Token (required)
    ASANA_WORKSPACE_GID: Your Asana Workspace GID (required)
""",
    )

    parser.add_argument(
        "-g",
        "--gid",
        default="1209719836385072",  # Default Sales Process GID
        help="Process GID to work with (default: 1209719836385072)",
    )

    parser.add_argument(
        "--onboarding-project",
        default=None,
        help="Target Onboarding project GID. If not specified, will attempt "
        "to discover from workspace via WorkspaceProjectRegistry.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without committing changes.",
    )

    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only discover workspace projects and exit (no automation).",
    )

    parser.add_argument(
        "--no-discovery",
        action="store_true",
        help="Disable automatic workspace project discovery.",
    )

    args = parser.parse_args()

    # Validate environment
    if not os.environ.get("ASANA_PAT"):
        print("Error: ASANA_PAT environment variable not set")
        print("Set it with: export ASANA_PAT='your_token_here'")
        sys.exit(1)

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
    if not workspace_gid:
        print("Error: ASANA_WORKSPACE_GID environment variable not set")
        print("Set it with: export ASANA_WORKSPACE_GID='your_workspace_gid'")
        sys.exit(1)

    # Determine discovery mode
    use_discovery = not args.no_discovery

    # Handle --discover-only mode
    if args.discover_only:

        async def _run_discovery() -> int:
            config = AsanaConfig()
            async with AsanaClient(
                config=config, workspace_gid=workspace_gid
            ) as client:
                return await demo_discover_projects_only(client)

        exit_code = asyncio.run(_run_discovery())
        sys.exit(exit_code)

    # Run the demo
    exit_code = asyncio.run(
        demo_pipeline_automation(
            process_gid=args.gid,
            onboarding_project_gid=args.onboarding_project,
            workspace_gid=workspace_gid,
            dry_run=args.dry_run,
            use_discovery=use_discovery,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
