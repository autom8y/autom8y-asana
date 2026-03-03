---
name: test-coverage-criteria
description: "Observation criteria for codebase test structure knowledge capture. Use when: theoros is producing test-coverage knowledge for .know/, documenting test gaps, coverage patterns, and testing conventions. Triggers: test coverage knowledge criteria, test structure observation, testing patterns documentation."
---

# Test Coverage Observation Criteria

> The theoros observes and documents codebase test structure -- producing a knowledge reference that enables any CC agent to understand what is tested, how tests are organized, and where coverage gaps exist.

## Language Detection

Before beginning observation, identify the primary language(s) in the project:
- Check for: `go.mod` (Go), `package.json` (JS/TS), `pyproject.toml`/`setup.py` (Python),
  `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (Java/Kotlin)
- Adapt scope targets, evidence collection, and tooling references accordingly

### Scope Adaptation

| Criteria Element | Go | TypeScript | Python |
|---|---|---|---|
| Test files | `*_test.go` | `*.test.ts`, `*.spec.ts` | `test_*.py`, `*_test.py` |
| Test runner command | `CGO_ENABLED=0 go test ./...` | `npx jest` or `npx vitest` | `pytest` or `python -m pytest` |
| Coverage tool | `go test -cover ./...` | `jest --coverage` or `vitest --coverage` | `pytest --cov` |
| Test data directories | `testdata/` | `__fixtures__/`, `fixtures/` | `fixtures/`, `testdata/` |
| Integration test signal | build tags (`//go:build integration`), `TestMain` | `*.integration.test.ts` | `@pytest.mark.integration` |

## Scope

**Target files**: Test files per language convention (see Scope Adaptation table), test data directories, test helper files

**Observation focus**: Coverage gaps, testing conventions, and test structure -- what a CC agent needs to understand before writing or modifying tests.

**NOTE**: This domain uses knowledge-capture grading. Instead of grading compliance ratios ("90% of packages have tests"), grade the COMPLETENESS of the test structure reference produced. A = comprehensive documentation of test structure with evidence. F = incomplete or inaccurate documentation.

## Criteria

### Criterion 1: Coverage Gaps (weight: 40%)

**What to observe**: Where tests are missing, weak, or incomplete -- and what critical paths are well-covered vs under-covered. The knowledge reference must tell an agent where new tests are most needed and what the highest-risk untested areas are.

**Evidence to collect**:
- Identify packages WITHOUT test files and assess their criticality (are untested packages in critical paths?)
- Document coverage for critical paths: CLI command handlers, sync pipeline, hook handlers -- note which have tests and which are missing
- Identify test blind spots: which code paths are not tested (error paths, edge cases, boundary conditions)
- Check for negative tests (testing that errors are returned, that invalid input is rejected) -- note where they are absent
- Note any coverage measurement infrastructure (go test -cover, CI coverage reports) and document coverage percentages if available
- Produce a prioritized gap list: which untested areas pose the highest risk?

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | All untested packages identified and criticality-assessed. Critical paths (CLI, sync, hooks) assessed for coverage. Blind spots cataloged. Prioritized gap list produced. An agent could immediately target the highest-value missing tests. |
| B | 80-89% completeness | Most untested packages identified. Critical paths assessed. Major blind spots noted. Gap list present but not fully prioritized. |
| C | 70-79% completeness | Some untested packages listed but not comprehensively. Critical path coverage partially assessed. Blind spots not systematically identified. |
| D | 60-69% completeness | Coverage mentioned vaguely ("some packages have tests") without specific analysis or prioritization. |
| F | < 60% completeness | Coverage gaps not assessed or critical path coverage not evaluated. |

---

### Criterion 2: Testing Conventions (weight: 30%)

**What to observe**: How tests are written and how test data is managed -- naming, structure, assertion patterns, fixture patterns, and idioms used consistently across the codebase. The knowledge reference must tell an agent how to write a test that fits.

**Evidence to collect**:
- Document test function naming conventions (e.g., `TestFoo`, `TestFoo_Bar`, subtest naming)
- Identify subtest patterns (`t.Run` usage, naming conventions within subtests)
- Note assertion patterns (stdlib comparisons, `t.Errorf`, helper packages)
- Document test helper patterns (`t.Helper()` usage, shared setup functions)
- Check for test skip patterns (`t.Skip`, build tags, environment checks)
- Identify `testdata/` directories and document their contents and usage patterns
- Document test fixture patterns (golden files, JSON fixtures, YAML test configs)
- Note test helper functions for creating test scenarios (temp dirs, test projects, mock data)
- Check for test environment management (`t.TempDir()`, env vars, temp file cleanup)
- Identify builder/factory patterns for test data construction

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | All testing conventions documented with examples from multiple packages. Naming, assertions, helpers, and skip patterns covered. Fixture patterns, testdata directory structure, and test environment management all documented. An agent could write tests matching project conventions. |
| B | 80-89% completeness | Major conventions documented with examples. Fixture patterns and helpers covered. Minor gaps in skip or environment patterns. |
| C | 70-79% completeness | Core conventions noted but examples limited to one or two packages. Fixture patterns partially documented. |
| D | 60-69% completeness | Some conventions and fixture information without examples or comprehensive coverage. |
| F | < 60% completeness | Testing conventions not documented, or fixture patterns not addressed. |

---

### Criterion 3: Test Structure Summary (weight: 30%)

**What to observe**: A high-level summary of how tests are distributed and structured across the codebase -- strengths and patterns, not a per-package table. The knowledge reference must give an agent a mental model of the test landscape without overwhelming detail.

**Evidence to collect**:
- Summarize overall test distribution: how many packages have tests vs not, in what ratio
- Identify the most heavily tested areas (by test count and test complexity) -- name the areas, not every file
- Note test package naming patterns (`package foo` vs `package foo_test` -- internal vs external tests)
- Identify integration test files vs unit test files (by naming, build tags, or test setup patterns)
- Document any test binary or TestMain patterns
- Note how tests are run (e.g., `CGO_ENABLED=0 go test ./...`) -- the test invocation command

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Clear summary of test distribution with coverage strengths and gaps. Package naming patterns (internal vs external) documented. Integration vs unit test distinction made. Test command documented. An agent has a complete mental model of the test landscape. |
| B | 80-89% completeness | Good distribution summary. Internal vs external test packages distinguished. Integration tests identified. Test command documented. Minor gaps. |
| C | 70-79% completeness | General structure described but integration test identification or package naming conventions incomplete. |
| D | 60-69% completeness | Some test structure information without systematic assessment or summary. |
| F | < 60% completeness | Test structure not summarized or significantly incomplete. |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Coverage Gaps: B (midpoint 85%) x 40% = 34.0
- Testing Conventions: A (midpoint 95%) x 30% = 28.5
- Test Structure Summary: B (midpoint 85%) x 30% = 25.5
- **Total: 88.0 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [architecture-criteria](architecture.lego.md) -- Codebase architecture knowledge capture
- [conventions-criteria](conventions.lego.md) -- Codebase conventions knowledge capture
