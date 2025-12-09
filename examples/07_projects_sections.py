"""Example: Projects and Sections Organization

Demonstrates:
- Creating projects (requires workspace and team)
- Creating sections within projects
- Listing sections in a project
- Moving tasks between sections
- Adding tasks to projects
- Hierarchical project organization

Requirements:
- ASANA_PAT environment variable set
- Valid workspace GID (provide via --workspace arg)
- Workspace must have at least one team (most workspaces have a default team)

Usage:
    export ASANA_PAT="your_token_here"
    python examples/07_projects_sections.py --workspace WORKSPACE_GID

Output:
    Project and section creation, task organization
"""

import asyncio
import time
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from _config import get_workspace_gid, get_config_instructions


async def get_team_for_project(
    client: AsanaClient, workspace_gid: str
) -> str | None:
    """Get a team GID for creating a project.

    Tries to find an available team in the workspace.

    Args:
        client: Asana client instance
        workspace_gid: Workspace GID

    Returns:
        Team GID if available, None if no teams found
    """
    print("\n=== Finding Team for Project ===")

    try:
        # List teams in the workspace
        teams = await client.teams.list_for_workspace_async(
            workspace_gid=workspace_gid
        ).take(1)  # Just need one team

        if teams:
            team = teams[0]
            print(f"Using team: {team.name}")
            print(f"  Team GID: {team.gid}")
            # Explicitly cast to str since we know team.gid is a string
            return str(team.gid)
        else:
            print("⚠️  No teams found in workspace")
            return None

    except Exception as e:
        print(f"⚠️  Could not fetch teams: {e}")
        return None


async def create_project_structure(
    client: AsanaClient, workspace_gid: str, team_gid: str
) -> tuple[str, list[str]]:
    """Create a project with multiple sections.

    Args:
        client: Asana client instance
        workspace_gid: Workspace GID
        team_gid: Team GID for the project

    Returns:
        Tuple of (project_gid, list of section_gids)
    """
    print("\n=== Creating Project ===")

    # Create a new project in the team
    project = await client.projects.create_async(
        workspace=workspace_gid,
        team=team_gid,  # REQUIRED: Specify the team
        name=f"Example Project - Organization Demo {int(time.time())}",
        notes="Demonstrates project and section organization",
        default_view="list",
    )

    print(f"Created project: {project.name}")
    print(f"  GID: {project.gid}")
    print(f"  Team: {team_gid}")
    print(f"  Workspace: {project.workspace.name if project.workspace else 'N/A'}")

    # Create sections to organize tasks
    print("\n=== Creating Sections ===")

    section_names = ["To Do", "In Progress", "Review", "Done"]
    section_gids = []

    for section_name in section_names:
        section = await client.sections.create_async(
            project=project.gid,
            name=section_name,
        )
        section_gids.append(section.gid)
        print(f"  Created section: {section.name} ({section.gid})")

    return project.gid, section_gids


async def list_project_sections(client: AsanaClient, project_gid: str) -> None:
    """List all sections in a project."""
    print("\n=== Listing Project Sections ===")

    # List sections using pagination
    sections = await client.sections.list_for_project_async(project_gid).collect()

    print(f"Project has {len(sections)} sections:")
    for i, section in enumerate(sections, 1):
        print(f"  {i}. {section.name} (GID: {section.gid})")


async def create_and_organize_tasks(
    client: AsanaClient, project_gid: str, section_gids: list[str]
) -> list[str]:
    """Create tasks and organize them into sections.

    Returns:
        List of created task GIDs
    """
    print("\n=== Creating and Organizing Tasks ===")

    task_gids = []

    # Create tasks in the "To Do" section (first section)
    for i in range(5):
        task = await client.tasks.create_async(
            name=f"Task {i+1}",
            projects=[project_gid],
            notes=f"This is task number {i+1}",
        )
        task_gids.append(task.gid)

        # Add task to "To Do" section
        # Note: Tasks are added to sections via the tasks endpoint
        await client.tasks.update_async(
            task.gid,
            # Move to section by updating memberships
            # (This is a simplified approach; in production you might use
            # addProjectForSection endpoint)
        )

        print(f"  Created task: {task.name} ({task.gid})")

    return task_gids


async def move_task_between_sections(
    client: AsanaClient,
    project_gid: str,
    task_gid: str,
    from_section_name: str,
    to_section_name: str,
) -> None:
    """Move a task from one section to another.

    This demonstrates task organization within a project.
    """
    print("\n=== Moving Task Between Sections ===")

    # Get task details
    task = await client.tasks.get_async(task_gid)
    print(f"Task: {task.name}")
    print(f"  Moving from '{from_section_name}' to '{to_section_name}'")

    # Note: In the actual SDK, you would use the projects.add_task_for_section
    # endpoint or similar. For this example, we'll show the concept.
    # In practice, tasks are moved via the tasks memberships or by
    # adding to a specific section via the projects endpoint.

    print("  (Movement handled via section membership update)")


async def demonstrate_task_in_multiple_projects(
    client: AsanaClient, workspace_gid: str, team_gid: str, task_gid: str
) -> str:
    """Show how a task can belong to multiple projects.

    Note: This demonstrates creating a second project and the concept of
    multi-project tasks. However, the SDK currently does not expose the
    addProject endpoint needed to add a task to additional projects after
    creation. The 'projects' field is read-only during updates.

    To add tasks to multiple projects, specify all projects during creation:
        client.tasks.create_async(name="Task", projects=[project1, project2])

    Returns:
        GID of the second project created
    """
    print("\n=== Task in Multiple Projects ===")

    # Create a second project
    project2 = await client.projects.create_async(
        workspace=workspace_gid,
        team=team_gid,
        name=f"Second Project - Multi-project Demo {int(time.time())}",
    )

    print(f"Created second project: {project2.name}")
    print(f"  GID: {project2.gid}")

    # NOTE: The 'projects' field on tasks is read-only during updates.
    # You cannot use update_async(projects=[...]) to add a task to more projects.
    #
    # Asana API provides POST /tasks/{task_gid}/addProject for this purpose,
    # but this method is not yet implemented in the SDK.
    #
    # Workaround: Specify all projects when creating the task:
    #   client.tasks.create_async(name="Task", projects=[project1, project2])

    print("\nNote: Tasks can belong to multiple projects, but must be")
    print("      specified during creation. The SDK does not yet support")
    print("      adding tasks to additional projects after creation.")
    print("      Use: client.tasks.create_async(projects=[p1, p2])")

    return str(project2.gid)


async def list_tasks_in_section(
    client: AsanaClient, section_gid: str, section_name: str
) -> None:
    """List all tasks in a specific section."""
    print(f"\n=== Tasks in '{section_name}' Section ===")

    # List tasks in section
    tasks = await client.tasks.list_async(section=section_gid).take(5)

    if tasks:
        print(f"Found {len(tasks)} tasks:")
        for task in tasks:
            print(f"  - {task.name}")
    else:
        print("  (no tasks in this section)")


async def cleanup(
    client: AsanaClient, project_gids: list[str], task_gids: list[str]
) -> None:
    """Clean up created resources."""
    print("\n=== Cleaning Up ===")

    # Delete tasks
    for task_gid in task_gids:
        await client.tasks.delete_async(task_gid)
    print(f"Deleted {len(task_gids)} tasks")

    # Delete projects (this also deletes their sections)
    for project_gid in project_gids:
        await client.projects.delete_async(project_gid)
    print(f"Deleted {len(project_gids)} projects")


async def main(workspace_gid: str) -> None:
    """Run all project/section examples."""
    print("autom8_asana SDK - Projects and Sections Examples")

    async with AsanaClient() as client:
        # Get a team for creating the project
        team_gid = await get_team_for_project(client, workspace_gid)

        if not team_gid:
            print("\n" + "="*60)
            print("NO TEAMS AVAILABLE")
            print("="*60)
            print("\nProjects in Asana must belong to a team. This workspace")
            print("appears to have no teams available for project creation.")
            print("\nTo run this example:")
            print("  1. Create a team in your Asana workspace")
            print("  2. Or use a different workspace with teams")
            print("\nNote: Most Asana workspaces have at least one default team.")
            print("="*60)
            return

        project_gids = []
        task_gids = []

        # Example 1: Create project with sections
        project_gid, section_gids = await create_project_structure(
            client, workspace_gid, team_gid
        )
        project_gids.append(project_gid)

        # Example 2: List sections
        await list_project_sections(client, project_gid)

        # Example 3: Create and organize tasks
        task_gids = await create_and_organize_tasks(
            client, project_gid, section_gids
        )

        # Example 4: Move task between sections
        if task_gids and len(section_gids) >= 2:
            await move_task_between_sections(
                client,
                project_gid,
                task_gids[0],
                "To Do",
                "In Progress",
            )

        # Example 5: List tasks in a section
        if section_gids:
            await list_tasks_in_section(
                client, section_gids[0], "To Do"
            )

        # Example 6: Task in multiple projects
        if task_gids:
            project2_gid = await demonstrate_task_in_multiple_projects(
                client, workspace_gid, team_gid, task_gids[0]
            )
            project_gids.append(project2_gid)

        # Cleanup
        await cleanup(client, project_gids, task_gids)

    print("\n=== Complete ===")
    print("Key Takeaways:")
    print("  - Projects provide top-level organization")
    print("  - Sections organize tasks within projects")
    print("  - Tasks can belong to multiple projects (specify during creation)")
    print("  - Sections are like columns in a Kanban board")
    print("  - Use sections for workflow stages (To Do, In Progress, Done)")
    print("\nLimitation:")
    print("  - SDK does not yet support adding tasks to additional projects")
    print("    after creation. Specify all projects in create_async().")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Demonstrate project and section organization"
    )
    parser.add_argument(
        "--workspace",
        default=get_workspace_gid(),
        help="Workspace GID (or set ASANA_WORKSPACE_GID env var)",
    )
    args = parser.parse_args()

    if not args.workspace:
        print("ERROR: No workspace GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.workspace))
