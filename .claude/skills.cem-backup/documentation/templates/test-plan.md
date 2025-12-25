# Test Plan Template

## When to Create a Test Plan

**Owner**: QA/Adversary
**Location**: `/docs/testing/TP-{feature-slug}.md`
**Purpose**: Defines HOW we validate the implementation meets requirements.

Create a Test Plan when:
- A feature is ready for QA validation
- Code complete handoff from Engineer
- Formalizing test coverage for a deliverable

---

## Template

```markdown
# Test Plan: {Feature Name}

## Metadata
- **TP ID**: TP-{NNNN}
- **Status**: Draft | In Review | Approved
- **Author**: {name}
- **Created**: {date}
- **PRD Reference**: PRD-{NNNN}
- **TDD Reference**: TDD-{NNNN}

## Test Scope
What is being tested? What is explicitly excluded?

## Requirements Traceability
| Requirement ID | Test Cases     | Coverage Status |
| -------------- | -------------- | --------------- |
| FR-001         | TC-001, TC-002 | Covered         |
| FR-002         | TC-003         | Covered         |
| NFR-001        | PERF-001       | Covered         |

## Test Cases

### Functional Tests
| TC ID  | Description     | Steps | Expected Result      | Priority |
| ------ | --------------- | ----- | -------------------- | -------- |
| TC-001 | {What it tests} | {How} | {What should happen} | High     |

### Edge Cases
| TC ID    | Description          | Input   | Expected Result     |
| -------- | -------------------- | ------- | ------------------- |
| EDGE-001 | {Boundary condition} | {Input} | {Expected behavior} |

### Error Cases
| TC ID   | Description  | Failure Condition | Expected Handling     |
| ------- | ------------ | ----------------- | --------------------- |
| ERR-001 | {What fails} | {How it fails}    | {How system responds} |

### Performance Tests
| PERF ID  | Scenario   | Target          | Measurement Method |
| -------- | ---------- | --------------- | ------------------ |
| PERF-001 | {Scenario} | {Target metric} | {How measured}     |

### Security Tests
| SEC ID  | Attack Vector | Test Method | Expected Defense     |
| ------- | ------------- | ----------- | -------------------- |
| SEC-001 | {Vector}      | {Method}    | {How system defends} |

## Test Environment
Requirements for test execution.

## Risks & Gaps
Known testing limitations or coverage gaps.

## Exit Criteria
What conditions must be met to consider testing complete?
```

---

## Quality Gates

A Test Plan is ready for approval when:

- [ ] All PRD requirements have traced test cases
- [ ] Edge cases identified
- [ ] Error cases covered
- [ ] Performance requirements have test methods
- [ ] Exit criteria are clear
