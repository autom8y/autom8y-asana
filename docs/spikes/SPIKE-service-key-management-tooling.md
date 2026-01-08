# Spike: Service Key Management Tooling Gap Analysis

**Date**: 2026-01-08
**Author**: Claude (R&D Agent)
**Status**: Complete
**Scope**: Auth service key management tooling

## Problem Statement

Managing service API keys in production is painful due to:
1. CLI command `revoke` not exposed (API exists, CLI doesn't expose it)
2. No `update` command to modify key attributes (e.g., add `--multi-tenant`)
3. Production database intentionally secured behind security groups
4. Current workaround requires psql + Secrets Manager manual operations

**Trigger**: User created key without `--multi-tenant` flag and couldn't easily fix it.

## Current State Analysis

### Admin API (✅ Complete)

The Admin API at `/internal/admin/service-keys` already supports full CRUD:

| Endpoint | Method | Status |
|----------|--------|--------|
| `/service-keys` | POST | ✅ Implemented |
| `/service-keys` | GET | ✅ Implemented |
| `/service-keys/{id}/rotate` | POST | ✅ Implemented |
| `/service-keys/{id_or_name}` | DELETE | ✅ Implemented |

**Key features**:
- DELETE accepts both UUID and name (convenient)
- Rate limiting (100 req/min)
- Requires `admin:keys` permission
- Full audit logging

### AdminAPIClient (✅ Complete)

The Python client in `service_key_manager.py` wraps all API endpoints:

```python
class AdminAPIClient:
    def create_key(name, multi_tenant, permissions, business_id) -> dict
    def list_keys(limit, offset) -> list[dict]
    def rotate_key(key_id) -> dict
    def revoke_key(key_id) -> None  # ✅ EXISTS!
```

### CLI Commands (❌ Gap)

| Command | Status | Notes |
|---------|--------|-------|
| `create` | ✅ | Works |
| `list` | ✅ | Works |
| `test` | ✅ | Token exchange testing |
| `validate` | ✅ | JWT validation |
| `rotate` | ✅ | Works |
| `resolve` | ✅ | ID resolution |
| `revoke` | ❌ | **Missing** - API and client exist |
| `update` | ❌ | **Missing** - API doesn't support PATCH |

## Gap Analysis

### Gap 1: Missing `revoke` CLI Command (Easy Fix)

**Severity**: Low (workaround exists)
**Effort**: ~30 minutes
**Impact**: High (unblocks immediate issue)

The `AdminAPIClient.revoke_key()` method exists but isn't exposed via CLI:

```python
# Existing (line 502-519):
def revoke_key(self, key_id: str) -> None:
    """Revoke service key via Admin API."""
    response = self._make_request(
        method="DELETE",
        path=f"/internal/admin/service-keys/{key_id}",
    )
```

**Fix**: Add `revoke` subparser and handler (copy pattern from `rotate`).

### Gap 2: No `update` API or CLI Command

**Severity**: Medium
**Effort**: ~2-4 hours (API + CLI)
**Impact**: Medium (rotate + recreate is workaround)

Currently no way to update key attributes:
- `allow_multi_tenant`
- `service_permissions`
- `business_id`

**Workaround**: Revoke + recreate with correct flags.

**Proper fix**: Add PATCH endpoint:

```python
@router.patch("/service-keys/{key_id}")
async def update_service_key(
    key_id: str,
    request: UpdateServiceKeyRequest,  # multi_tenant, permissions
) -> ServiceKeyInfo:
```

## Recommendations

### Option A: Minimal Fix (Recommended for Now)

Add `revoke` CLI command only. Users can then:

```bash
# Delete the broken key
python scripts/service_key_manager.py revoke asana-cache-warmer

# Recreate with correct flags
python scripts/service_key_manager.py create asana-cache-warmer --multi-tenant
```

**Pros**:
- Minimal code change (~40 lines)
- Unblocks immediate issue
- Uses existing, tested API

**Cons**:
- Key value changes (need to update Secrets Manager)

### Option B: Full CRUD (Future Enhancement)

Add both `revoke` and `update` commands with PATCH API.

**Pros**:
- Complete key lifecycle management
- No key value changes for attribute updates

**Cons**:
- More implementation time
- PATCH semantics need design (which fields updatable?)

### Option C: Admin Dashboard (Long-term)

Build web UI for service key management.

**Pros**:
- Better UX for non-developers
- Visual audit trail
- Role-based access

**Cons**:
- Significant investment
- Overkill for current team size

## Implementation Plan (Option A)

### Step 1: Add `revoke` subparser (CLI)

```python
# In main() after rotate_parser:
revoke_parser = subparsers.add_parser(
    "revoke",
    help="Revoke (delete) a service key",
    description="Permanently revoke a service API key. The key will immediately stop working.",
)
revoke_parser.add_argument(
    "name",
    help="Service key name or UUID to revoke",
)
```

### Step 2: Add handler function

```python
def handle_revoke(args: argparse.Namespace, config: EnvironmentConfig) -> int:
    """Handle revoke command."""
    console = Console()

    # Resolve name to key info
    key_info = resolve_key_by_name(args.name, config)
    if not key_info:
        console.print(f"[red]Key '{args.name}' not found[/red]")
        return EXIT_FAILURE

    # Confirm unless --force
    if not args.force:
        confirm = Confirm.ask(f"Revoke key '{key_info['name']}'? This cannot be undone")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return EXIT_SUCCESS

    # Revoke via API
    client = get_admin_api_client(config)
    client.revoke_key(key_info["id"])

    # Delete from Secrets Manager
    secrets = SecretsManagerClient()
    secret_path = f"{config.secrets_prefix}/{key_info['name']}"
    try:
        secrets.delete(secret_path)
    except SecretsError:
        pass  # Secret may not exist

    console.print(f"[green]✓ Key '{key_info['name']}' revoked[/green]")
    return EXIT_SUCCESS
```

### Step 3: Wire up in main()

```python
elif args.command == "revoke":
    return handle_revoke(args, env_config)
```

## Immediate Workaround

Until CLI is updated, user can fix their key via ECS Exec:

```bash
# 1. Get container task ARN
TASK_ARN=$(aws ecs list-tasks --cluster prod-cluster --service-name auth-service --query 'taskArns[0]' --output text)

# 2. Exec into container
aws ecs execute-command \
    --cluster prod-cluster \
    --task $TASK_ARN \
    --container auth \
    --interactive \
    --command "python scripts/service_key_manager.py create asana-cache-warmer-v2 --multi-tenant"

# 3. Update Secrets Manager manually
aws secretsmanager put-secret-value \
    --secret-id autom8y/auth/service-api-keys/asana-cache-warmer \
    --secret-string "<new_key_value>"
```

## Decision

**Recommendation**: Implement Option A (add `revoke` CLI command) as immediate fix.

This is a ~30 minute change that:
1. Exposes already-tested API functionality
2. Follows existing CLI patterns
3. Unblocks the immediate user need
4. Is low-risk (DELETE API already in production)

Option B (PATCH/update) can be a follow-up if frequent attribute changes become a pattern.

## Files to Modify

| File | Change |
|------|--------|
| `services/auth/scripts/service_key_manager.py` | Add `revoke` subparser + handler |

## References

- Admin API: `services/auth/src/routes/admin.py`
- CLI Tool: `services/auth/scripts/service_key_manager.py`
- API Schemas: `services/auth/src/schemas/admin.py`
