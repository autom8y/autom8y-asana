# Process Smells (PR-*)

> Issues in development workflow, testing, and documentation.

## Smell Types

| Smell Type | ID Pattern | Description | Example |
|------------|------------|-------------|---------|
| Missing Tests | PR-TEST | Code without test coverage | New feature with 0% coverage |
| Flaky Tests | PR-FLAKY | Tests that fail intermittently | Random CI failures |
| Slow Tests | PR-SLOW | Tests exceeding time thresholds | 30-second unit test |
| Outdated Docs | PR-DOCS | Documentation not matching code | API docs referencing removed endpoints |
| TODO Accumulation | PR-TODO | Growing TODO/FIXME count | 50+ unresolved TODOs |
| Disabled Tests | PR-SKIP | Tests marked skip/pending | `it.skip('should work')` |

## Detection Heuristics

### PR-TEST: Missing Tests

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Coverage tools: `jest --coverage`, `go test -cover` | Set coverage thresholds; flag violations |
| **Semi-Automated** | Coverage trend analysis | Track coverage over time; identify declining areas |
| **Manual** | Critical path identification | Prioritize tests for high-risk code paths |

### PR-FLAKY: Flaky Tests

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | CI history analysis: same test, different outcomes | Parse CI logs for intermittent failures |
| **Semi-Automated** | Retry detection | Flag tests that pass only after retries |
| **Manual** | Root cause investigation | Identify timing issues, race conditions, external dependencies |

### PR-SLOW: Slow Tests

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Test timing reports | Use `--testTimeout` flags; flag tests exceeding threshold |
| **Semi-Automated** | Threshold configuration | Adjust thresholds by test type (unit vs. integration) |
| **Manual** | Acceptable vs. problematic | Assess if slowness is inherent or fixable |

### PR-DOCS: Outdated Docs

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Link checking, API comparison tools | Check for broken links, mismatched signatures |
| **Semi-Automated** | Documentation review | Compare docs with actual code behavior |
| **Manual** | Accuracy verification | Validate examples, tutorials still work |

### PR-TODO: TODO Accumulation

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Grep `TODO\|FIXME\|HACK\|XXX`, count tracking | Monitor TODO count over time |
| **Semi-Automated** | Age analysis (git blame) | Identify oldest TODOs; prioritize resolution |
| **Manual** | Priority assessment | Distinguish critical TODOs from aspirational notes |

### PR-SKIP: Disabled Tests

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Grep `skip\|pending\|xdescribe\|xit` | Find all disabled tests |
| **Semi-Automated** | Reason documentation | Check if skip reason is documented |
| **Manual** | Re-enable feasibility | Assess if test can be fixed and re-enabled |

## Usage Guidance

### Detection Order

1. Run automated test coverage and timing analysis
2. Review CI history for flaky test patterns
3. Manually audit documentation accuracy and TODO priorities

### Common False Positives

| Smell | False Positive | How to Identify |
|-------|----------------|-----------------|
| PR-TEST | Intentionally untested code | Verify if code is test harness, generated code, or trivial |
| PR-FLAKY | Environment-specific failures | Distinguish flaky from environment configuration issues |
| PR-SLOW | Integration test suites | Integration tests legitimately take longer |
| PR-DOCS | Versioned documentation | Old docs may be intentionally preserved for older versions |
| PR-TODO | Aspirational TODOs | Not all TODOs require immediate action |
| PR-SKIP | Known issues with workarounds | Tests may be disabled with documented alternatives |

### Remediation Strategies

| Smell | Remediation Approach |
|-------|---------------------|
| PR-TEST | Write missing tests, add coverage enforcement to CI |
| PR-FLAKY | Fix race conditions, mock external dependencies, increase timeouts |
| PR-SLOW | Optimize test setup, use test doubles, run slow tests separately |
| PR-DOCS | Generate docs from code, add doc validation to CI |
| PR-TODO | Convert TODOs to issues, schedule resolution, remove stale TODOs |
| PR-SKIP | Fix and re-enable tests, document why test is disabled, set re-enable deadline |

### Testing Best Practices

| Practice | Rationale | Example |
|----------|-----------|---------|
| **Unit tests** | Fast feedback, isolate failures | Test functions in isolation with mocks |
| **Integration tests** | Verify component interaction | Test API endpoints with real database |
| **Coverage thresholds** | Enforce minimum coverage | Fail CI if coverage < 80% |
| **Fast by default** | Developer productivity | Unit tests complete in <1s |
| **Deterministic** | Reliable CI | No randomness, no time dependencies |
| **Independent** | Parallel execution | Tests don't share mutable state |

### Documentation Standards

| Type | Update Trigger | Validation |
|------|----------------|------------|
| **API docs** | Public interface change | Auto-generate from types/annotations |
| **README** | Setup process change | Test installation steps in CI |
| **Changelog** | Release | Link to commits/PRs |
| **Architecture docs** | Major refactoring | Review in design sessions |
| **Runbooks** | Incident | Validate steps work as documented |

### Integration with Severity

Process smells typically have **medium-to-high** severity because:
- **Medium-high impact**: Poor testing/docs increase risk of bugs and onboarding friction
- **Medium-high frequency**: Process issues compound over time
- **Low-medium blast radius**: Usually affects team workflow rather than end users
- **Medium fix complexity**: Fixing tests/docs requires discipline and time

See [severity/defaults.md](../severity/defaults.md) for specific default severity factors per smell type.

## Related Patterns

- **DC-COMMENT**: Commented code may include disabled tests
- **AR-LEAK**: Leaky abstractions often result from missing integration tests
- **CX-CYCLO**: Complex code is harder to test, leading to missing tests
- **PR-TODO** accumulation may indicate **AR-DIVERGE** (file changing for many reasons)
