---
name: doc-security
description: "Security-pack templates for threat modeling, compliance, penetration testing, and security reviews. Use when: conducting threat analysis, mapping compliance controls, documenting penetration tests, providing security signoffs. Triggers: threat model, STRIDE, DREAD, compliance requirements, SOC 2, GDPR, HIPAA, pentest, penetration test, security review, security signoff."
---

# Security Documentation Templates

Templates for security analysis, compliance, testing, and approval workflows.

## Template Index

1. [Threat Model Template](#threat-model-template) - STRIDE/DREAD analysis and risk assessment
2. [Compliance Requirements Template](#compliance-requirements-template) - Regulatory mapping and control implementation
3. [Pentest Report Template](#pentest-report-template) - Vulnerability findings and exploitation details
4. [Security Signoff Template](#security-signoff-template) - Code review and release approval

---

## Threat Model Template {#threat-model-template}

```markdown
# THREAT-{slug}

## Executive Summary
{One paragraph overview of security posture}

## Scope
- **Assets**: {What we're protecting}
- **Threat Actors**: {Who might attack}
- **Trust Boundaries**: {Where trust changes}

## Data Flow Diagram
{ASCII or description of data flows}

## Threat Analysis

### STRIDE Analysis
| Component | S | T | R | I | D | E | Notes |
|-----------|---|---|---|---|---|---|-------|
| {component} | {rating} | ... |

### Identified Threats

#### THREAT-001: {Name}
- **Category**: {STRIDE category}
- **DREAD Score**: {D+R+E+A+D = total}
- **Attack Vector**: {How it would be exploited}
- **Impact**: {What damage results}
- **Mitigation**: {How to prevent/detect}
- **Status**: {Open/Mitigated/Accepted}

## Recommendations
1. {Priority 1 mitigation}
2. {Priority 2 mitigation}

## Residual Risks
{Threats accepted or deferred}
```

---

## Compliance Requirements Template {#compliance-requirements-template}

```markdown
# COMPLY-{slug}

## Overview
{What feature/system and which regulations}

## Applicable Regulations

### {Regulation 1, e.g., SOC 2}
- **Relevant Criteria**: {CC6.1, CC7.2, etc.}
- **Scope**: {What's covered}

### {Regulation 2, e.g., GDPR}
- **Relevant Articles**: {Art. 6, Art. 32, etc.}
- **Scope**: {What's covered}

## Control Requirements

### {Control Category, e.g., Access Control}

#### CTRL-001: {Control Name}
- **Regulation**: {Source requirement}
- **Requirement**: {What must be true}
- **Implementation**: {How to achieve}
- **Evidence**: {What proves compliance}
- **Testing**: {How to validate}

#### CTRL-002: {Control Name}
...

## Data Classification
| Data Element | Classification | Retention | Encryption |
|--------------|---------------|-----------|------------|
| {element} | {PII/Sensitive/Public} | {period} | {at-rest/in-transit} |

## Gap Analysis
| Control | Current State | Gap | Remediation | Priority |
|---------|--------------|-----|-------------|----------|
| {control} | {state} | {gap} | {fix} | {P1/P2/P3} |

## Implementation Checklist
- [ ] {Requirement 1}
- [ ] {Requirement 2}

## Evidence Collection
| Control | Evidence Type | Collection Method | Frequency |
|---------|--------------|-------------------|-----------|
| {control} | {logs/configs/screenshots} | {automated/manual} | {continuous/quarterly} |

## Audit Readiness
{Steps to prepare for audit}
```

---

## Pentest Report Template {#pentest-report-template}

```markdown
# PENTEST-{slug}

## Executive Summary
- **Scope**: {What was tested}
- **Duration**: {Testing period}
- **Critical Findings**: {count}
- **High Findings**: {count}
- **Overall Risk**: {Critical/High/Medium/Low}

## Scope and Methodology

### In Scope
- {System/component 1}
- {System/component 2}

### Out of Scope
- {What wasn't tested}

### Methodology
{Testing approach: black box, gray box, white box}

### Tools Used
- {Tool 1}: {Purpose}
- {Tool 2}: {Purpose}

## Findings Summary
| ID | Title | Severity | Status |
|----|-------|----------|--------|
| VULN-001 | {title} | {Critical/High/Medium/Low} | {Open/Fixed} |

## Detailed Findings

### VULN-001: {Title}

**Severity**: {Critical/High/Medium/Low}
**CVSS Score**: {X.X}
**Status**: {Open/Fixed/Accepted}

#### Description
{What the vulnerability is}

#### Affected Components
- {Component 1}
- {Component 2}

#### Technical Details
{How the vulnerability works}

#### Reproduction Steps
1. {Step 1}
2. {Step 2}
3. {Step 3}

#### Proof of Concept
```
{Code or commands to reproduce}
```

#### Evidence
{Screenshots, logs, or other evidence}

#### Impact
{What an attacker could do}

#### Remediation
{Specific fix recommendation}

#### References
- {CVE, CWE, or other references}

### VULN-002: {Title}
...

## Attack Paths
{How vulnerabilities chain together}

## Positive Findings
{Security controls that worked well}

## Recommendations
1. **Immediate**: {Critical fixes}
2. **Short-term**: {High priority fixes}
3. **Medium-term**: {Improvements}

## Appendix
- Testing logs
- Tool output
- Additional evidence
```

---

## Security Signoff Template {#security-signoff-template}

```markdown
# SEC-{slug}

## Review Summary
- **PR/Change**: {Link or description}
- **Reviewed By**: security-reviewer
- **Date**: {date}
- **Decision**: {Approved / Approved with Conditions / Rejected}

## Change Overview
{What this change does from security perspective}

## Security Scope

### High-Risk Areas Touched
- [ ] Authentication
- [ ] Authorization
- [ ] Input handling
- [ ] Data encryption
- [ ] PII processing
- [ ] External integrations
- [ ] Secrets management

### Threat Model Reference
{Link to relevant threat model if exists}

## Findings

### Critical (Must Fix)
{None or list}

### High (Should Fix)
{None or list}

### Medium (Recommend Fix)
{None or list}

### Low (Consider)
{None or list}

### Finding Details

#### FINDING-001: {Title}
- **Severity**: {Critical/High/Medium/Low}
- **Location**: {File:line}
- **Issue**: {Description}
- **Risk**: {What could go wrong}
- **Recommendation**: {How to fix}
- **Status**: {Open/Fixed/Accepted}

## Security Checklist

### Authentication
- [ ] Auth required for sensitive endpoints
- [ ] Token validation correct
- [ ] Session handling secure

### Authorization
- [ ] Access controls enforced
- [ ] No privilege escalation paths
- [ ] Role checks in place

### Input Validation
- [ ] All inputs validated
- [ ] Proper encoding/escaping
- [ ] No injection vulnerabilities

### Data Protection
- [ ] Sensitive data encrypted
- [ ] No secrets in code
- [ ] Logging doesn't leak PII

### Error Handling
- [ ] No stack traces exposed
- [ ] Error messages safe
- [ ] Failures secure

## Decision

### Verdict
{Approved / Approved with Conditions / Rejected}

### Conditions (if applicable)
1. {Condition 1}
2. {Condition 2}

### Rationale
{Why this decision}

### Risk Acceptance (if applicable)
{Any risks being accepted and why}

## Follow-up Required
- [ ] {Action item if any}

## Sign-off
Reviewed and approved/rejected by Security Reviewer on {date}.
```

---

## Related Resources

See `documentation` skill for development artifact templates (PRD, TDD, ADR, Test Plans).
