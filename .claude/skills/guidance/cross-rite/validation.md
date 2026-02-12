# Cross-Rite Handoff Validation

> Hook integration specification for `ari hook handoff-validate`.

## Overview

The `handoff-validate` hook checks that required artifacts exist and are complete before cross-rite handoff. It integrates with `/wrap` to catch missing handoffs for SERVICE+ complexity work.

## Command Usage

```bash
ari hook handoff-validate --route=<route> [--skip-artifacts] [--json]
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--route` | Yes | Target route: `sre`, `security`, or `doc` |
| `--skip-artifacts` | No | Skip artifact existence checks (for non-standard workflows) |
| `--json` | No | Output results as JSON |

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All checks passed | Proceed with handoff |
| 1 | Required artifacts missing | Create missing artifacts |
| 2 | Artifacts incomplete | Complete required sections |
| 3 | Route not recognized | Check route parameter |

## Route Checks

### SRE Route (`--route=sre`)

```bash
ari hook handoff-validate --route=sre
```

**Checks performed**:

| Check | Required | Description |
|-------|----------|-------------|
| `deployment-manifest` | Yes | Looks for `deploy/`, `k8s/`, or `docker-compose.yaml` |
| `runbook` | Yes | Looks for `docs/runbooks/*.md` matching service name |
| `env-documentation` | Yes | Looks for env var docs or `.env.example` |
| `resource-requirements` | Yes | Validates resources defined in deployment manifest |
| `health-endpoints` | Warn | Checks for `/health` route definition |

**Example output**:
```
Validating handoff: 10x-to-sre
================================

[PASS] deployment-manifest
       Found: deploy/kubernetes/my-service.yaml

[PASS] runbook
       Found: docs/runbooks/my-service.md

[PASS] env-documentation
       Found: docs/config/env-vars.md

[PASS] resource-requirements
       CPU: 100m-500m, Memory: 256Mi-512Mi

[WARN] health-endpoints
       /health endpoint not detected (manual check needed)

Result: READY FOR HANDOFF (1 warning)
```

### Security Route (`--route=security`)

```bash
ari hook handoff-validate --route=security
```

**Checks performed**:

| Check | Required | Description |
|-------|----------|-------------|
| `threat-model` | Yes | Looks for `docs/security/threat-model-*.md` |
| `auth-documentation` | Yes | Checks handoff artifact for auth section |
| `secret-scan` | Yes | Scans source for hardcoded secrets |
| `dependency-audit` | Yes | Runs `npm audit`/`pip-audit`/equivalent |
| `input-validation` | Warn | Identifies endpoints needing manual review |

**Example output**:
```
Validating handoff: 10x-to-security
====================================

[PASS] threat-model
       Found: docs/security/threat-model-auth-flow.md

[PASS] auth-documentation
       Auth flow documented in handoff artifact

[PASS] secret-scan
       No hardcoded secrets detected in src/

[PASS] dependency-audit
       0 critical, 0 high, 2 medium vulnerabilities
       (Medium: lodash@4.17.20, axios@0.21.0)

[WARN] input-validation
       3 endpoints identified for manual review:
       - POST /api/upload (file handling)
       - POST /api/users (user input)
       - GET /api/search (query params)

Result: READY FOR HANDOFF (1 warning)
```

### Doc Route (`--route=doc`)

```bash
ari hook handoff-validate --route=doc
```

**Checks performed**:

| Check | Required | Description |
|-------|----------|-------------|
| `feature-summary` | Yes | Checks handoff artifact for feature section |
| `api-changes` | Conditional | Required if new/modified endpoints detected |
| `config-changes` | Conditional | Required if new env vars detected |
| `migration-notes` | Conditional | Required if breaking changes detected |
| `user-impact` | Warn | Prompts for user impact assessment |

**Example output**:
```
Validating handoff: 10x-to-doc
===============================

[PASS] feature-summary
       Feature summary provided in handoff artifact

[PASS] api-changes
       2 new endpoints documented
       1 deprecated endpoint documented

[PASS] config-changes
       3 new environment variables documented

[WARN] migration-notes
       Breaking change detected in API schema
       Ensure rollback procedure is documented

[INFO] user-impact
       Affects: all users
       Action required: none (automatic)
       Communication: release notes recommended

Result: READY FOR HANDOFF (1 warning)
```

## Integration with /wrap

The `/wrap` command integrates handoff validation:

```
/wrap flow:
1. Run quality gates
2. Check complexity level
3. If SERVICE+ complexity:
   a. Check for pending handoffs in SESSION_CONTEXT
   b. Suggest required handoffs based on session artifacts
   c. Offer to run handoff-validate
4. If handoff validation fails:
   a. Display missing artifacts
   b. Offer --skip-handoff to bypass (logged)
5. Complete wrap
```

### Bypass Flags

```bash
# Skip handoff checks during wrap (not recommended)
/wrap --skip-handoff

# Skip artifact existence checks in validation
ari hook handoff-validate --route=sre --skip-artifacts
```

**When to use `--skip-artifacts`**:
- Non-standard project structure
- Documentation in external system
- Prototype/spike work (use with `--skip-checks`)

All bypasses are logged to SESSION_CONTEXT for audit trail.

## Error Messages

| Error | Cause | Resolution |
|-------|-------|------------|
| `HANDOFF-V001: Missing deployment manifest` | No deploy config found | Create deployment configuration |
| `HANDOFF-V002: Missing runbook` | No runbook for service | Create runbook with startup/shutdown/troubleshooting |
| `HANDOFF-V003: Secrets detected` | Hardcoded secrets in source | Move secrets to environment/secret store |
| `HANDOFF-V004: Critical vulnerabilities` | npm/pip audit found criticals | Update dependencies before handoff |
| `HANDOFF-V005: Missing threat model` | No threat model for security handoff | Create STRIDE analysis document |
| `HANDOFF-V006: Missing feature summary` | No feature description for doc handoff | Add feature summary to handoff artifact |
| `HANDOFF-V007: Undocumented API changes` | New endpoints without documentation | Document API changes in handoff artifact |

## JSON Output

For CI/CD integration:

```bash
ari hook handoff-validate --route=sre --json
```

```json
{
  "route": "sre",
  "status": "pass",
  "checks": [
    {"name": "deployment-manifest", "status": "pass", "path": "deploy/kubernetes/my-service.yaml"},
    {"name": "runbook", "status": "pass", "path": "docs/runbooks/my-service.md"},
    {"name": "env-documentation", "status": "pass", "path": "docs/config/env-vars.md"},
    {"name": "resource-requirements", "status": "pass", "details": {"cpu": "100m-500m", "memory": "256Mi-512Mi"}},
    {"name": "health-endpoints", "status": "warn", "message": "Manual check needed"}
  ],
  "warnings": 1,
  "errors": 0,
  "ready_for_handoff": true
}
```

## Implementation Notes

The `handoff-validate` hook is implemented as an Ariadne CLI command. Implementation details:

1. **Route configuration**: Each route defines required and optional checks
2. **Path resolution**: Uses project-relative paths, respects `.claude/` conventions
3. **Artifact parsing**: Reads HANDOFF artifacts from session directory
4. **Integration**: Called by `/wrap` quality gate phase

For hook implementation details, see `.claude/hooks/` and Ariadne CLI source.
