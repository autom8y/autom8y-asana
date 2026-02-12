# 10x-to-Security Handoff Checklist

> Artifact checklist for handing off security-sensitive work to security.

## When to Use

This route is **required** when:
- Authentication or authorization logic changes
- Cryptographic operations implemented
- Secrets management modified
- User data handling (PII, credentials, tokens)
- External input processing (APIs, file uploads, user input)
- Third-party integrations with security implications

## Artifact Checklist

### Threat Model

- [ ] STRIDE analysis completed for new components
  - [ ] Spoofing: Identity verification reviewed
  - [ ] Tampering: Data integrity controls documented
  - [ ] Repudiation: Audit logging in place
  - [ ] Information Disclosure: Data exposure points identified
  - [ ] Denial of Service: Rate limiting and resource controls
  - [ ] Elevation of Privilege: Authorization boundaries defined
- [ ] Trust boundaries documented
- [ ] Data flow diagram showing security-relevant paths
- [ ] Attack surface identified and minimized

**Location**: `docs/security/threat-model-{feature}.md` or handoff artifact

### Authentication/Authorization Flows

- [ ] Authentication mechanism documented (OAuth, JWT, session, API key)
- [ ] Token lifecycle documented (issuance, refresh, revocation)
- [ ] Authorization model defined (RBAC, ABAC, ACL)
- [ ] Permission matrix provided (role -> resource -> action)
- [ ] Session management reviewed (timeout, invalidation, concurrent sessions)
- [ ] Failed authentication handling documented (lockout, alerts)

**Format**:
```
| Role | Resource | Read | Write | Delete | Admin |
|------|----------|------|-------|--------|-------|
| user | /profile | self | self  | -      | -     |
| admin| /profile | all  | all   | all    | yes   |
```

### Security-Relevant Code Paths

- [ ] Input validation documented (what inputs, what validation)
- [ ] Output encoding documented (context-appropriate escaping)
- [ ] Cryptographic operations reviewed
  - [ ] Algorithm choices documented (AES-256-GCM, bcrypt, etc.)
  - [ ] Key management approach
  - [ ] No custom crypto implementations
- [ ] SQL/NoSQL injection prevention documented
- [ ] Path traversal prevention documented
- [ ] SSRF prevention documented (for external URL handling)

**Location**: Reference specific files with line numbers

```
Security-relevant paths:
- src/auth/login.ts:45-120 - Authentication logic
- src/api/upload.ts:30-80 - File upload validation
- src/utils/crypto.ts - Encryption utilities
```

### Dependency Audit

- [ ] Dependency audit run (`npm audit`, `pip-audit`, `go mod verify`)
- [ ] No critical/high vulnerabilities in production dependencies
- [ ] Known vulnerabilities documented with mitigation timeline
- [ ] Dependency update plan for security patches

**Format**:
```
Audit Date: 2026-01-05
Tool: npm audit

| Package | Severity | CVE | Status |
|---------|----------|-----|--------|
| lodash  | High | CVE-2024-xxxxx | Updated to 4.17.21 |
| axios   | Medium | CVE-2024-xxxxx | Mitigated via config |
```

### Secrets Handling

- [ ] No secrets hardcoded in source code
- [ ] Secrets stored in approved secret store
- [ ] Secret rotation procedure documented
- [ ] Access to secrets properly scoped (least privilege)
- [ ] Secret exposure in logs prevented

## Validation

Run before handoff:
```bash
ari hook handoff-validate --route=security
```

Expected output:
```
[PASS] Threat model exists: docs/security/threat-model-feature.md
[PASS] Auth flow documented in handoff artifact
[PASS] No hardcoded secrets detected (scanned src/)
[PASS] Dependency audit clean: 0 critical, 0 high
[WARN] Input validation: 3 endpoints need manual review
```

## HANDOFF Artifact Template

Create `HANDOFF-10x-dev-to-security-YYYY-MM-DD.md`:

```yaml
---
artifact_id: HANDOFF-10x-dev-to-security-2026-01-05
schema_version: "1.0"
source_rite: 10x-dev
target_rite: security
handoff_type: assessment
priority: high
blocking: true
initiative: "feature-name"
created_at: "2026-01-05T12:00:00Z"
status: pending
items:
  - id: SEC-001
    summary: "Review authentication flow for new login feature"
    priority: critical
    assessment_questions:
      - "Is the JWT implementation following best practices?"
      - "Are there any token exposure risks in the current flow?"
      - "Is the session timeout appropriate for this use case?"
  - id: SEC-002
    summary: "Validate input sanitization for file upload endpoint"
    priority: high
    assessment_questions:
      - "Are all file types properly validated?"
      - "Is there path traversal protection?"
      - "What is the maximum file size and is it enforced?"
source_artifacts:
  - "src/auth/login.ts"
  - "src/api/upload.ts"
  - "docs/security/threat-model-feature.md"
---
```

## After Handoff

Security rite will:
1. Review threat model completeness
2. Audit security-relevant code paths
3. Verify cryptographic implementations
4. Check for common vulnerabilities (OWASP Top 10)
5. Return HANDOFF-RESPONSE with findings and recommendations

## Common Issues

| Issue | Resolution |
|-------|------------|
| Missing threat model | Use STRIDE template, focus on data flows |
| Incomplete auth documentation | Document all auth states and transitions |
| Hardcoded secrets found | Move to environment variables or secret store |
| Outdated dependencies | Update before handoff, document exceptions |
| Custom crypto | Replace with standard library implementations |
