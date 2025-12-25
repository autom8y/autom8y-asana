# security-pack

> Security assessment, threat modeling, and compliance

## Overview

The security team for threat modeling, compliance mapping, penetration testing, and security review. Ensures code and systems meet security standards before release.

## Switch Command

```bash
/security
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **threat-modeler** | opus | Maps attack vectors (STRIDE/DREAD) |
| **compliance-architect** | opus | Translates regulations to requirements |
| **penetration-tester** | sonnet | Probes for vulnerabilities |
| **security-reviewer** | opus | Final gate before merge |

## Workflow

```
threat-modeling → compliance-design → penetration-testing → security-review
       │                 │                    │                   │
       ▼                 ▼                    ▼                   ▼
   THREAT-*          COMPLY-*            PENTEST-*             SEC-*
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **PATCH** | Single file, no auth/crypto | Minimal |
| **FEATURE** | New endpoints, data handling | Feature |
| **SYSTEM** | Auth, crypto, external integrations | Full system |

## Best For

- Pre-release security review
- Threat modeling new features
- Compliance mapping (SOC 2, GDPR, HIPAA)
- Penetration testing
- Security code review

## Not For

- Feature development → use 10x-dev-pack
- General code quality → use hygiene-pack
- Operational security → coordinate with sre-pack

## Quick Start

```bash
/security                      # Switch to team
/task "Security review for payment feature"
```

## Common Patterns

### Pre-Release Review

```bash
/security
/task "Security review for v2.0 release" --complexity=SYSTEM
```

### Feature Security

```bash
/security
/task "Threat model for OAuth integration" --complexity=FEATURE
```

### Quick Security Check

```bash
/security
/task "Review input validation changes" --complexity=PATCH
```

## Integration with Development

```bash
# Feature touches auth:
/security                      # Threat model first
/10x                          # Implement with security context
/security                      # Final security review
```

## Related Commands

- `/task` - Full security lifecycle
- `/code-review` - Can invoke security-reviewer
