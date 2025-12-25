---
name: security-ref
description: |
  Reference documentation for Security Team.
  Use when: learning about security-pack agents, understanding the security workflow,
  invoking security agents. Triggers: security-pack, security team, threat-modeler,
  compliance-architect, penetration-tester, security-reviewer.
---

# Security Team (security-pack)

> Map threats. Enforce compliance. Test defenses. Guard the gate.

## Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Agents | `~/Code/roster/teams/security-pack/agents/` | Agent prompts |
| Workflow | `~/Code/roster/teams/security-pack/workflow.yaml` | Phase configuration |
| Switch | `/security` | Activate this team |

## Team Roster

| Agent | Model | Role | Produces |
|-------|-------|------|----------|
| **threat-modeler** | opus | Maps attack vectors with STRIDE/DREAD | threat-model |
| **compliance-architect** | opus | Translates regulations to requirements | compliance-requirements |
| **penetration-tester** | sonnet | Probes systems for vulnerabilities | pentest-report |
| **security-reviewer** | opus | Final security gate before merge | security-signoff |

## Workflow

```
threat-modeling → compliance-design → penetration-testing → security-review
       │                 │                    │                   │
       ▼                 ▼                    ▼                   ▼
  THREAT-{slug}    COMPLY-{slug}       PENTEST-{slug}        SEC-{slug}
```

### Phase Details

| Phase | Agent | Input | Output |
|-------|-------|-------|--------|
| threat-modeling | threat-modeler | Feature specs | Threat model with STRIDE analysis |
| compliance-design | compliance-architect | Threat model | Control requirements |
| penetration-testing | penetration-tester | Control requirements | Vulnerability findings |
| security-review | security-reviewer | Pentest report | Merge approval/rejection |

## Complexity Levels

| Level | Scope | Phases |
|-------|-------|--------|
| **PATCH** | Single file, no auth/crypto | penetration-testing, security-review |
| **FEATURE** | New endpoints, data handling | All phases |
| **SYSTEM** | Auth, crypto, external integrations | All phases |

## Command Mapping

| Command | Maps To | Use When |
|---------|---------|----------|
| `/security` | Team switch | Activating this team |
| `/architect` | compliance-architect | Compliance mapping only |
| `/build` | penetration-tester | Testing only |
| `/qa` | security-reviewer | Review only |
| `/hotfix` | penetration-tester | Quick security fix |
| `/code-review` | security-reviewer | Security code review |

## When to Use This Team

**Use security-pack when:**
- New feature touches auth, crypto, or PII
- Preparing for compliance audit
- Need pre-release security validation
- Reviewing code with security implications

**Don't use security-pack when:**
- Pure documentation changes → Use doc-team-pack
- General code quality → Use hygiene-pack
- Feature development → Use 10x-dev-pack

## Agent Summaries

### Threat Modeler

**Purpose**: Map attack vectors before code ships

**Key Responsibilities**:
- STRIDE/DREAD analysis
- Kill chain mapping
- Attack surface enumeration
- Risk prioritization

**Produces**: `docs/security/THREAT-{slug}.md`

---

### Compliance Architect

**Purpose**: Translate regulations into engineering requirements

**Key Responsibilities**:
- Control mapping (SOC 2, GDPR, HIPAA)
- Gap analysis
- Evidence architecture
- Audit preparation

**Produces**: `docs/security/COMPLY-{slug}.md`

---

### Penetration Tester

**Purpose**: Probe systems like an authorized adversary

**Key Responsibilities**:
- Vulnerability discovery
- Exploit development
- Attack path documentation
- Remediation guidance

**Produces**: `docs/security/PENTEST-{slug}.md`

---

### Security Reviewer

**Purpose**: Final security gate before merge

**Key Responsibilities**:
- Security code review
- Fix validation
- Release approval
- Pattern recognition

**Produces**: `docs/security/SEC-{slug}.md`

## Cross-References

- **Related Skills**: @standards (secure coding)
- **Team Packs**: 10x-dev-pack (implementation), sre-pack (infrastructure security)
- **Commands**: See COMMAND_REGISTRY.md
