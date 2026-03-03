---
name: doc-artifacts-test
description: "Test case and test summary templates. Use when: writing individual test cases, producing a QA test summary, documenting release readiness. Triggers: test case, test summary, QA, release recommendation, test plan."
---

# Test Templates

## Test Case Template

```markdown
## TC-[number]: [Test case name]

**Requirement**: [Link to PRD requirement or success criterion]
**Priority**: High / Medium / Low
**Type**: Functional / Security / Performance / Edge Case

### Preconditions
- [Required state before test]

### Steps
1. [Action]
2. [Action]
3. [Action]

### Expected Result
[What should happen]

### Actual Result
[What did happen] - PASS / FAIL

### Notes
[Any observations, variations, or follow-up items]
```

## Test Summary Template

```markdown
# Test Summary: [Feature Name]

## Overview
- **Test Period**: [dates]
- **Tester**: QA Adversary
- **Build/Version**: [identifier]

## Results Summary
| Category | Pass | Fail | Blocked | Not Run |
|----------|------|------|---------|---------|
| Acceptance Criteria | | | | |
| Edge Cases | | | | |
| Security | | | | |
| Performance | | | | |

## Critical Defects
[List of critical/high defects with status]

## Release Recommendation
**[GO / NO-GO / CONDITIONAL]**

[Rationale for recommendation]

## Known Issues
[Issues that are acceptable for release, with justification]

## Risks
[Identified risks and their likelihood/impact]

## Not Tested
[What wasn't tested and why]
```
