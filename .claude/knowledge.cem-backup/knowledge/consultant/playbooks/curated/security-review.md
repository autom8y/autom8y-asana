# Playbook: Security Review

> Pre-release security assessment and validation

## When to Use

- Feature touches auth/crypto/PII
- Pre-release security gate
- Compliance requirement
- Security concern raised
- External integration

## Prerequisites

- Code or design to review
- Understanding of security requirements
- Compliance framework if applicable

## Command Sequence

### Phase 1: Switch to Security Team

```bash
/security
```
**Expected output**: Team switched to security-pack

### Phase 2: Start Security Session

```bash
/start "Security review for [feature]" --complexity=FEATURE
```
**Expected output**: Session created, threat-modeler invoked
**Decision point**: Complexity levels:
- PATCH: Single file, no auth/crypto
- FEATURE: New endpoints, data handling
- SYSTEM: Auth, crypto, external integrations

### Phase 3: Threat Modeling

Threat Modeler performs STRIDE/DREAD analysis.

**Expected output**: THREAT-{slug}.md with attack vectors

### Phase 4: Compliance Design

Compliance Architect maps to requirements.

**Expected output**: COMPLY-{slug}.md with control requirements

### Phase 5: Penetration Testing

Penetration Tester probes for vulnerabilities.

**Expected output**: PENTEST-{slug}.md with findings

### Phase 6: Security Review

Security Reviewer makes final determination.

**Expected output**: SEC-{slug}.md with approval/rejection

**Decision point**:
- Approved → Proceed to ship
- Rejected → Fix issues, re-review

### Phase 7: Wrap Up

```bash
/wrap
```
**Expected output**: Security review summary

## Variations

- **Quick check**: PATCH complexity for minor changes
- **Compliance-focused**: Emphasize compliance-architect phase
- **Penetration-focused**: Emphasize testing phase

## Success Criteria

- [ ] Threat model complete
- [ ] Compliance requirements mapped
- [ ] Vulnerabilities tested
- [ ] Security sign-off obtained
- [ ] Findings documented

## Integration with Development

```bash
# Security-sensitive feature:
/security                      # Threat model first
/10x                          # Implement
/security                      # Final review
```

## Emergency Path

Critical security fix:
```bash
/security
/hotfix                        # Fast-track fix
/security                      # Validate fix
```
