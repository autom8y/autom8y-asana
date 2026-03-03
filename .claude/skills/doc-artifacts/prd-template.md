---
name: doc-artifacts-prd
description: "PRD template with impact assessment. Use when: writing a product requirements document, assessing feature impact, defining acceptance criteria. Triggers: PRD, product requirements, impact assessment, user stories, functional requirements."
---

# PRD Template

```markdown
# PRD: [Feature Name]

## Overview
[2-3 sentence summary of what and why]

## Impact Assessment
<!-- Required for workflow routing -->
impact: [low | high]
impact_categories: []  <!-- Only populate when impact: high -->

### Impact Categories Reference
- security: Authentication, authorization, encryption, secrets
- data_model: Schema changes, migrations, data integrity
- api_contract: Public API changes, breaking changes, versioning
- auth: Permission model, access control, identity
- cross_service: Multi-service coordination, distributed transactions

### Impact Determination
Flag high-impact when ANY of these apply:
- Changes to authentication/authorization flows
- Database schema modifications
- Public API contract changes
- Security-sensitive code paths
- Cross-service dependencies

## Background
[Context: why now, what problem, who's affected]

## User Stories
- As a [role], I want [capability], so that [benefit]

## Functional Requirements
### Must Have
- FR-1: [requirement]
- FR-2: [requirement]

### Should Have
- FR-3: [requirement]

### Could Have
- FR-4: [requirement]

## Non-Functional Requirements
- NFR-1: Performance - [specific metric]
- NFR-2: Security - [specific requirement]

## Edge Cases
| Case | Expected Behavior |
|------|------------------|
| [scenario] | [behavior] |

## Success Criteria
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]

## Out of Scope
- [Explicitly excluded item]

## Open Questions
- [Any unresolved items - ideally none at handoff]
```

## Impact Assessment Examples

**Example 1: Low Impact (UI enhancement)**
```markdown
## Impact Assessment
impact: low
impact_categories: []

Rationale: Styling changes only, no backend modifications, no security implications.
```

**Example 2: High Impact (API change)**
```markdown
## Impact Assessment
impact: high
impact_categories: [api_contract, data_model]

Rationale: Adding new field to user profile requires schema migration and API contract update.
```

**Example 3: High Impact (Security)**
```markdown
## Impact Assessment
impact: high
impact_categories: [security, auth]

Rationale: Modifying password reset flow affects authentication and security-sensitive code.
```
