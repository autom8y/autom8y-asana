"""Shared configuration helper for example scripts.

Provides environment variable configuration support for workspace and project GIDs,
allowing examples to run without command-line arguments when defaults are set.

Environment Variables:
    ASANA_WORKSPACE_GID: Default workspace GID for examples
    ASANA_WORKSPACE_KEY: Indirection key - points to env var containing workspace GID
                         (for ECS deployments where secrets use platform naming)
    ASANA_PROJECT_GID: Default project GID for examples

Usage:
    from _config import get_workspace_gid, get_project_gid, get_config_instructions

    parser.add_argument(
        "--workspace",
        default=get_workspace_gid(),
        help="Workspace GID (or set ASANA_WORKSPACE_GID env var)"
    )

    args = parser.parse_args()

    if not args.workspace:
        print("ERROR: No workspace GID provided")
        print(get_config_instructions())
        exit(1)
"""

import os


def get_workspace_gid() -> str | None:
    """Get default workspace GID with indirection support.

    Supports ASANA_WORKSPACE_KEY indirection (parallels ASANA_TOKEN_KEY pattern):
    - Set ASANA_WORKSPACE_KEY=WORKSPACE_GID to read from WORKSPACE_GID env var
    - Defaults to reading from ASANA_WORKSPACE_GID if no indirection set

    This enables ECS deployments where secrets are injected with platform naming
    conventions (e.g., WORKSPACE_GID from Secrets Manager) without requiring
    env var bridging in task definitions.

    Returns:
        Workspace GID if set, None otherwise
    """
    key = os.environ.get("ASANA_WORKSPACE_KEY", "ASANA_WORKSPACE_GID")
    return os.getenv(key)


def get_project_gid() -> str | None:
    """Get default project GID from ASANA_PROJECT_GID environment variable.

    Returns:
        Project GID if set, None otherwise
    """
    return os.getenv("ASANA_PROJECT_GID")


def get_config_instructions() -> str:
    """Return setup instructions for configuring environment variables.

    Returns:
        Multi-line string with setup instructions
    """
    return """
To configure default GIDs for examples, set these environment variables:

1. Find your workspace GID:
   - Method 1 (Web URL): Open Asana, go to any project
     URL format: https://app.asana.com/0/WORKSPACE_GID/PROJECT_GID

   - Method 2 (SDK):
     from autom8_asana import AsanaClient
     async with AsanaClient() as client:
         workspaces = await client.workspaces.list_async().collect()
         for ws in workspaces:
             print(f"{ws.name}: {ws.gid}")

2. Find your project GID:
   - Method 1 (Web URL): Open the project, the GID is in the URL
   - Method 2 (SDK):
     from autom8_asana import AsanaClient
     async with AsanaClient() as client:
         projects = await client.projects.list_async(workspace="WORKSPACE_GID").take(10)
         for proj in projects:
             print(f"{proj.name}: {proj.gid}")

3. Set environment variables:
   # Bash/Zsh (add to ~/.bashrc or ~/.zshrc for persistence)
   export ASANA_WORKSPACE_GID="your_workspace_gid"
   export ASANA_PROJECT_GID="your_project_gid"

   # Or for current session only
   ASANA_WORKSPACE_GID="your_workspace_gid" python examples/02_task_crud.py

4. Optional: Use direnv for project-specific configuration
   # Install direnv: https://direnv.net/
   # Create .envrc in project root:
   echo 'export ASANA_WORKSPACE_GID="your_workspace_gid"' > .envrc
   echo 'export ASANA_PROJECT_GID="your_project_gid"' >> .envrc
   direnv allow

5. ECS/Platform Deployments (env var indirection):
   The SDK supports ASANA_TOKEN_KEY and ASANA_WORKSPACE_KEY for indirection.
   This allows reading secrets from platform-named env vars without bridging.

   # Example: ECS task injects WORKSPACE_GID from Secrets Manager
   export ASANA_WORKSPACE_KEY="WORKSPACE_GID"  # Points to WORKSPACE_GID env var
   export WORKSPACE_GID="your_workspace_gid"   # Injected by ECS

   # Example: ECS task injects BOT_PAT from Secrets Manager
   export ASANA_TOKEN_KEY="BOT_PAT"            # Points to BOT_PAT env var
   export BOT_PAT="your_pat_here"              # Injected by ECS

Note: You can still override defaults with command-line arguments:
  python examples/02_task_crud.py --workspace OTHER_WORKSPACE_GID
""".strip()
