# ADR-0014: Environment Variable Configuration for Example Scripts

**Status:** Accepted
**Date:** 2025-12-09
**Deciders:** Principal Engineer
**Tags:** examples, dx, configuration

## Context

The autom8_asana SDK includes 10 example scripts demonstrating key features. Prior to this change, 8 of 10 scripts failed on first run because they required command-line arguments for workspace and/or project GIDs:

- `02_task_crud.py` - requires `--workspace`
- `03_pagination.py` - requires `--project`
- `04_batch_create.py` - requires `--project`
- `05_batch_update.py` - requires `--project`
- `06_custom_fields.py` - requires `--workspace` AND `--project`
- `07_projects_sections.py` - requires `--workspace`
- `08_webhooks.py` - requires `--project`
- `10_error_handling.py` - requires `--workspace`

### User Pain Point

Users had to provide GIDs on every run:
```bash
python examples/02_task_crud.py --workspace 1143357799778608
python examples/03_pagination.py --project 1143843662099250
python examples/06_custom_fields.py --workspace 1143357799778608 --project 1143843662099250
```

This created friction:
1. Copy-paste GIDs repeatedly
2. Remember which examples need which GIDs
3. Long command lines reduced readability
4. Inconsistent with SDK's pattern of using `ASANA_PAT` environment variable

### Requirements

- Allow users to set default GIDs once and run all examples
- Maintain backward compatibility with CLI arguments
- CLI arguments must override environment variable defaults
- No secrets committed to git
- Zero external dependencies
- Clear error messages when GIDs are not provided

## Decision

Implement environment variable configuration using a shared helper module with the following components:

### 1. Shared Configuration Helper (`examples/_config.py`)

```python
def get_workspace_gid() -> str | None:
    """Get default workspace GID from ASANA_WORKSPACE_GID env var."""
    return os.getenv("ASANA_WORKSPACE_GID")

def get_project_gid() -> str | None:
    """Get default project GID from ASANA_PROJECT_GID env var."""
    return os.getenv("ASANA_PROJECT_GID")

def get_config_instructions() -> str:
    """Return setup instructions for users."""
    # Multi-line instructions with GID discovery methods
```

### 2. Modified argparse Pattern

Change from `required=True` to `default=get_workspace_gid()`:

```python
from _config import get_workspace_gid, get_config_instructions

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
```

### 3. Environment Variables

- `ASANA_WORKSPACE_GID` - Default workspace GID for examples
- `ASANA_PROJECT_GID` - Default project GID for examples

### 4. Documentation Updates

- `examples/README.md` - Configuration section with setup instructions
- `.gitignore` - Add `.envrc` for direnv users

## Alternatives Considered

### Alternative 1: Config File (config.json, .env)

**Rejected** - Requires external dependencies (python-dotenv) or custom parsing. Risk of users accidentally committing secrets to git. More complex than environment variables.

### Alternative 2: Interactive Prompts

**Rejected** - Breaks automation and scripting. Cannot be used in CI/CD. Annoying for repeated runs.

### Alternative 3: Hardcoded Defaults

**Rejected** - Not portable across users. Requires code changes to customize. Risk of committing user-specific GIDs to repository.

### Alternative 4: Template Scripts

**Rejected** - Duplicates code. Maintenance burden. Users must copy-paste and modify templates before running.

## Rationale

### Why This Approach

1. **Consistency with SDK patterns**: The SDK already uses `ASANA_PAT` environment variable for authentication. Using environment variables for GIDs maintains pattern consistency.

2. **Zero dependencies**: No `python-dotenv` or YAML parsers needed. Works with standard library `os.getenv()`.

3. **Simple one-time setup**: Users set environment variables once (or add to shell config) and all examples work.

4. **CLI override flexibility**: Command-line arguments take precedence, allowing per-run customization.

5. **No secrets in git**: Environment variables are user-managed and never committed. `.envrc` is in `.gitignore` for direnv users.

6. **Clear error messages**: When GIDs are missing, users see helpful setup instructions via `get_config_instructions()`.

7. **Backward compatible**: Existing scripts using CLI arguments continue to work exactly as before.

### Implementation Details

- **Validation after parsing**: argparse doesn't error on `None` defaults, so explicit validation is required after `args = parser.parse_args()`.

- **Shared helper module**: Centralizes configuration logic and error messages. Updates apply to all examples instantly.

- **Import placement**: Imports added near other imports, not in `__main__`, for clarity.

- **No SDK dependencies in _config.py**: The helper module uses only standard library, making it lightweight and fast.

## Consequences

### Positive

- **Improved developer experience**: Run examples without arguments after one-time setup
- **Reduced friction**: No copy-pasting GIDs for every example run
- **Better onboarding**: New users can explore examples quickly
- **Consistent with SDK patterns**: Matches `ASANA_PAT` environment variable approach
- **Flexible**: CLI arguments still available for override
- **Secure**: No secrets in git, environment variables are user-managed
- **Zero dependencies**: No external libraries needed
- **Clear errors**: Setup instructions displayed when GIDs missing

### Negative

- **One-time setup required**: Users must discover their GIDs and set environment variables (mitigated by comprehensive documentation)
- **Additional file**: `examples/_config.py` added to codebase (minimal, 100 lines)
- **Environment variable management**: Users must understand shell environment variables (standard practice, well-documented)

### Neutral

- **Not a breaking change**: CLI arguments still work, behavior unchanged for users already providing arguments
- **Documentation overhead**: README.md updated with configuration instructions (improves overall documentation quality)

## Compliance

- **No secrets committed**: `.envrc` in `.gitignore`
- **Zero dependencies**: Standard library only
- **Backward compatible**: CLI arguments unchanged
- **Clear error messages**: Setup instructions via `get_config_instructions()`

## Related Decisions

- **ADR-0001**: Protocol-Based Extensibility - Similar pattern of configuration flexibility
- **SDK authentication**: Uses `ASANA_PAT` environment variable (establishes pattern)

## References

- Approved plan: `/Users/tomtenuta/.claude/plans/groovy-seeking-abelson.md`
- User's workspace GID: `1143357799778608`
- User's project GID: `1143843662099250` (Business Offers project)

## Follow-up Tasks

- Monitor user feedback on environment variable setup
- Consider adding GID discovery helper script if users struggle with finding GIDs
- Evaluate extending pattern to other SDK configuration options if beneficial
