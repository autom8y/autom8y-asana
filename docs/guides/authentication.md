# Authentication Guide

This guide covers authentication patterns for the autom8y-asana SDK across different deployment scenarios.

## Overview

The SDK uses an `AuthProvider` protocol to abstract credential retrieval. This allows the same SDK code to work in:

- Local development (environment variables)
- ECS Fargate deployments (injected secrets)
- Direct AWS Secrets Manager access (runtime retrieval)
- Custom authentication systems

## Authentication Patterns

### Pattern 1: Environment Variables (Default)

The simplest pattern for local development and ECS deployments where secrets are injected as environment variables.

```python
import os
from autom8_asana import AsanaClient

# Set via environment variable
os.environ["ASANA_PAT"] = "your_personal_access_token"

# SDK reads from ASANA_PAT automatically
client = AsanaClient()
```

In ECS Fargate, the Terraform `service-stateless` stack automatically injects secrets as environment variables:

| Secret Name | Environment Variable |
|-------------|---------------------|
| `bot_pat` | `BOT_PAT` |
| `workspace_gid` | `WORKSPACE_GID` |

### Pattern 2: Direct Token

Pass the token directly when you have it available (useful for testing or pass-through APIs):

```python
from autom8_asana import AsanaClient

# User provides their PAT (multi-tenant API pattern)
client = AsanaClient(token="user_provided_pat")
```

### Pattern 3: AWS Secrets Manager (Platform Services)

For services that need to fetch credentials at runtime (e.g., secret rotation without restart):

```python
from autom8_asana import AsanaClient, SecretsManagerAuthProvider

# Create provider for autom8y/asana/* secrets
provider = SecretsManagerAuthProvider(service_name="asana")

# SDK will fetch autom8y/asana/bot_pat when needed
client = AsanaClient(auth_provider=provider)
```

**Requirements:**
- Install with AWS extras: `pip install autom8y-asana[aws]`
- IAM role must have `secretsmanager:GetSecretValue` permission for `autom8y/asana/*`

**Secret Naming Convention:**
```
autom8y/{service}/{credential}
```

Examples:
- `autom8y/asana/bot_pat` - Bot Personal Access Token
- `autom8y/asana/workspace_gid` - Workspace identifier

### Pattern 4: Custom Provider

Implement the `AuthProvider` protocol for custom authentication:

```python
from autom8_asana import AuthProvider, AsanaClient

class MyVaultProvider:
    """Custom auth provider for HashiCorp Vault."""

    def get_secret(self, key: str) -> str:
        # Your Vault integration here
        return vault_client.read(f"secret/data/asana/{key}")["data"][key]

client = AsanaClient(auth_provider=MyVaultProvider())
```

## ECS Fargate Deployment

The autom8y platform uses a standardized pattern for ECS deployments:

### Terraform Configuration

```hcl
# terraform/services/asana/main.tf
module "service" {
  source = "../../modules/platform/stacks/service-stateless"

  name = "asana"

  # Secrets are created in AWS Secrets Manager
  # Naming: autom8y/asana/{key}
  additional_secrets = {
    "bot_pat" = {
      description   = "Asana Bot Personal Access Token"
      initial_value = null  # Set via AWS CLI
    }
    "workspace_gid" = {
      description   = "Asana Workspace GID"
      initial_value = null
    }
  }

  # Secrets injected as environment variables:
  # BOT_PAT, WORKSPACE_GID
}
```

### Setting Secret Values

After Terraform creates the secrets, populate them via AWS CLI:

```bash
# Set the bot PAT (never commit this!)
aws secretsmanager put-secret-value \
  --secret-id autom8y/asana/bot_pat \
  --secret-string "your_actual_pat_here"

# Set the workspace GID
aws secretsmanager put-secret-value \
  --secret-id autom8y/asana/workspace_gid \
  --secret-string "1234567890123456"
```

### IAM Permissions

The ECS task role automatically has access via prefix-based IAM policy:

```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": "arn:aws:secretsmanager:*:*:secret:autom8y/asana/*"
}
```

## Multi-Tenant API Pattern

The autom8_asana API uses a pass-through pattern where each user provides their own PAT:

```python
# API endpoint (FastAPI)
async def get_tasks(
    authorization: str = Header(),
) -> list[Task]:
    pat = authorization.removeprefix("Bearer ")

    async with AsanaClient(token=pat) as client:
        return await client.tasks.list_async()
```

For service-level operations (background jobs), use `SecretsManagerAuthProvider`:

```python
# Background job that runs as the service bot
from autom8_asana import AsanaClient, SecretsManagerAuthProvider

async def sync_projects():
    provider = SecretsManagerAuthProvider(service_name="asana")

    async with AsanaClient(auth_provider=provider) as client:
        # Uses bot_pat from Secrets Manager
        projects = await client.projects.list_async()
```

## Secret Rotation

### With Environment Variables (ECS)

Restart the ECS service after updating the secret:

```bash
aws ecs update-service --cluster autom8y --service autom8y-asana-service --force-new-deployment
```

### With SecretsManagerAuthProvider

Clear the cache to pick up new secrets immediately:

```python
provider = SecretsManagerAuthProvider(service_name="asana")
client = AsanaClient(auth_provider=provider)

# After secret rotation
provider.clear_cache()

# Next call fetches fresh secret
client.tasks.get("task_gid")
```

## Security Best Practices

1. **Never commit secrets** - Use environment variables or Secrets Manager
2. **Use IAM roles** - ECS task roles provide automatic credential management
3. **Scope permissions** - Use prefix-based policies (`autom8y/asana/*`)
4. **Rotate regularly** - Implement secret rotation procedures
5. **Audit access** - Enable CloudTrail for Secrets Manager API calls

## Troubleshooting

### AuthenticationError: Environment variable 'ASANA_PAT' not set

The SDK expects `ASANA_PAT` by default. Check:
1. Environment variable is set correctly
2. Or provide a custom `AuthProvider`

### Access denied to secret

Check IAM permissions:
```bash
aws sts get-caller-identity
aws secretsmanager get-secret-value --secret-id autom8y/asana/bot_pat
```

### boto3 not installed

Install AWS extras:
```bash
pip install autom8y-asana[aws]
```
