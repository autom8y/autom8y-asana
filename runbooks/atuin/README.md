# autom8_asana Runbooks

Atuin Desktop runbooks for the autom8_asana SDK and API service. These runbooks provide executable workflows for authentication, development, and API operations.

---

## First Time Setup

### 1. Path Configuration (Automatic)

The runbooks use portable path variables instead of hardcoded paths. On first run of `00-bootstrap.md`, your repository path is automatically configured.

**What happens:**
- Creates `~/.config/autom8y/paths.env` if it doesn't exist
- Registers `AUTOM8Y_ASANA_PATH` pointing to your repository location
- Future runbook commands use this variable instead of hardcoded paths

**Manual setup (if needed):**
```bash
# Run from the autom8_asana repository root
just bootstrap-paths

# Verify configuration
just check-paths
```

### 2. Direnv Users (Optional)

If you use direnv, the `.envrc` file is already configured:
```bash
direnv allow
```

This auto-loads path configuration when you enter the directory.

---

## Prerequisites: Asana Personal Access Token

Before using these runbooks, obtain a Personal Access Token (PAT):

1. Go to [Asana Developer Console](https://app.asana.com/0/my-apps)
2. Click "Create new token"
3. Name it (e.g., "autom8_asana development")
4. Copy the token (only shown once!)

This token is required for all Asana API operations.

---

## Mental Model

```
ASANA API                    AUTOM8_ASANA SERVICE
===========                  ====================
                             00-bootstrap (env setup)
Personal Access Token -----> 01-authentication (PAT test)
                             -> 02-local-development
                             -> 03-api-operations
                             -> 04-troubleshooting
```

---

## Runbook Index

| # | File | Purpose | Time | Prerequisites |
|---|------|---------|------|---------------|
| 00 | [00-bootstrap.md](./00-bootstrap.md) | Environment setup, PAT configuration | ~3 min | Asana PAT |
| 01 | [01-authentication.md](./01-authentication.md) | PAT validation, Asana API access | ~5 min | 00 complete |
| 02 | [02-local-development.md](./02-local-development.md) | Dev server, testing, Docker | varies | 01 complete |
| 03 | [03-api-operations.md](./03-api-operations.md) | API endpoints, CRUD operations | varies | 01 complete |
| 04 | [04-troubleshooting.md](./04-troubleshooting.md) | Diagnostics, common issues | as needed | - |

---

## Quick Start

1. Obtain Asana PAT (see Prerequisites above)
2. Run `just setup-env` to create `~/.config/autom8y/envs/autom8-asana/runbook.env`
3. Add your `ASANA_PAT` to the env file
4. Open this folder in Atuin Desktop
5. Run `00-bootstrap.md` to verify setup (~3 min)

**Note:** Environment is automatically loaded by justfile commands. No `direnv allow` needed.

---

## Environment Variables

Required variables in `~/.config/autom8y/envs/autom8-asana/runbook.env`:

```bash
# Required
ASANA_PAT=your_personal_access_token

# Optional (with defaults)
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

---

## Authentication

autom8_asana uses Asana Personal Access Tokens (PAT) directly. Unlike other autom8y services, no cross-service authentication is required.

| Component | Value |
|-----------|-------|
| Auth Method | Bearer Token |
| Token Source | Asana Developer Console |
| Header | `Authorization: Bearer <PAT>` |
| Rate Limit | 1500 requests/minute |

---

## Related Resources

- [Asana Developer Console](https://app.asana.com/0/my-apps) - Generate PAT
- [Asana API Documentation](https://developers.asana.com/docs) - API reference
- [autom8_asana SDK Documentation](../docs/) - SDK usage guides

---

## Troubleshooting

See [04-troubleshooting.md](./04-troubleshooting.md) for detailed solutions.

### Quick Reference

| Error | Cause | Action |
|-------|-------|--------|
| 401 Unauthorized | Invalid/expired PAT | Regenerate at Asana |
| 403 Forbidden | No access to resource | Check workspace permissions |
| 429 Rate Limited | Too many requests | Wait for Retry-After header |
| Missing ASANA_PAT | Not configured | Run `just setup-env` |
| Path not configured | Missing paths.env | Run `just bootstrap-paths` |
| Server not responding | Not running | Run `just serve-api` |

