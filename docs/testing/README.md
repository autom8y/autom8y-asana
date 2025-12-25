# Test and Validation Documentation

## What Is This Directory?

This directory contains **Validation Plans (VPs)** and **Test Plans (TPs)** that verify features meet requirements and work correctly. These documents are created after implementation, before shipping to production.

## Document Types

### Validation Plans (VPs)
Format: `VP-FEATURE-NAME.md`

Post-implementation validation reports that confirm:
- All requirements from PRD are met
- Implementation matches TDD design
- Edge cases are handled
- Performance meets targets
- Ready for production

**When to create**: After feature implementation is complete, before merging to main or deploying.

Examples:
- `VP-CACHE-INTEGRATION.md`
- `VP-WORKSPACE-PROJECT-REGISTRY.md`
- `VP-SPRINT-1-PATTERN-COMPLETION.md`

### Test Plans (TPs)
Format: `TP-NNNN-feature-name.md` or `TP-FEATURE-NAME.md`

Detailed test scenarios and adversarial test cases:
- Happy path scenarios
- Error conditions
- Boundary cases
- Integration testing
- Performance benchmarks

**When to create**: During or after implementation, especially for complex features requiring structured testing.

Examples:
- `TP-0001-sdk-phase1-parity.md`
- `TP-0009-savesession-reliability.md`
- `TP-DETECTION.md`

## Naming Conventions

### Validation Plans (Preferred)
Format: `VP-FEATURE-NAME.md`
Example: `VP-CACHE-INTEGRATION.md`

Use descriptive feature names that match corresponding PRD/TDD names.

### Test Plans (Legacy and Current)
- **Numbered**: `TP-NNNN-feature-name.md` (e.g., `TP-0001-sdk-phase1-parity.md`)
- **Named**: `TP-FEATURE-NAME.md` (e.g., `TP-DETECTION.md`)

Both formats are valid. Choose based on project conventions.

## Status Lifecycle

Every validation document has a status. See [/docs/CONVENTIONS.md](../CONVENTIONS.md) for complete lifecycle specification.

### Validation Plan Status Values
1. **In Progress** - Validation underway, testing not complete
2. **APPROVED** - All tests passed, feature validated for production
3. **APPROVED-WITH-RESERVATIONS** - Passed with minor issues noted
4. **REJECTED** - Failed validation, implementation needs fixes
5. **INVALIDATED** - Validation superseded (feature changed or removed)

### Test Plan Status Values
1. **Draft** - Test scenarios being written
2. **Active** - Tests being executed
3. **Complete** - All test scenarios executed and documented

**Critical Rule**: Status in document frontmatter is canonical. Update status as validation progresses.

## Relationship to Other Docs

Validation documents verify implementation against requirements and design:

| Validates | Referenced By | Purpose |
|-----------|---------------|---------|
| PRD requirements | VP document | Confirms all requirements met |
| TDD architecture | VP document | Verifies design implemented correctly |
| Feature behavior | TP document | Documents test coverage |

**Typical flow**:
1. **PRD** defines what to build
2. **TDD** defines how to build it
3. **Implementation** builds the code
4. **TP** executes test scenarios
5. **VP** validates against requirements and approves for production

## When to Create Validation Documents

Create a **Validation Plan (VP)** when:
- Feature implementation is complete
- Feature is ready for production consideration
- Sprint or initiative needs validation before close
- Stakeholders need verification that requirements are met

Create a **Test Plan (TP)** when:
- Feature has complex testing requirements
- Adversarial testing is needed
- Test scenarios must be documented for repeatability
- Multiple testers need coordinated test approach

## VP Structure

All Validation Plans should include:

1. **Metadata** - Status, feature references, validation date
2. **Scope** - What is being validated (link to PRD/TDD)
3. **Validation Criteria** - Success conditions from PRD
4. **Test Results** - Evidence of testing performed
5. **Findings** - Issues discovered, limitations noted
6. **Verdict** - APPROVED, APPROVED-WITH-RESERVATIONS, or REJECTED
7. **Recommendations** - Follow-up work if any

## Creating a New Validation Plan

1. Identify feature name (match PRD/TDD naming)
2. Copy template from existing VP (e.g., VP-CACHE-INTEGRATION.md)
3. Use format: `VP-FEATURE-NAME.md`
4. Fill out metadata (status, references to PRD/TDD)
5. Document validation criteria from PRD
6. Execute tests and record results
7. Write findings and recommendations
8. Set status based on outcome:
   - `APPROVED` - All criteria met, ready for production
   - `APPROVED-WITH-RESERVATIONS` - Met with minor issues noted
   - `REJECTED` - Failed validation, needs rework
9. Commit with message: `docs(validation): Add VP-FEATURE-NAME validation report`

## Archival Policy

Archive validation documents when:
1. **Feature superseded** - Original feature replaced by new implementation
2. **Validation invalidated** - Feature changed significantly, validation no longer accurate
3. **Historical record only** - Feature stable for 6+ months, no active validation needed

### Archive Process

```bash
# Move to archive with quarter designation
git mv docs/testing/VP-OLD-FEATURE.md docs/.archive/validation/2025-Q4/
```

Update document with archive notice:

```markdown
> **ARCHIVE NOTICE**: This validation report has been archived.
> Reason: [Feature superseded | Feature removed | Validation invalidated]
> See [replacement document] for current validation.
```

**Note**: APPROVED validation reports are often kept indefinitely as evidence of feature quality.

## Finding Validation Documents

To find validation for a specific feature:
```bash
grep -l "FEATURE-NAME" docs/testing/VP-*.md
```

To see all approved validations:
```bash
grep -l "status.*APPROVED" docs/testing/VP-*.md
```

To check validation status for a sprint:
```bash
ls docs/testing/VP-SPRINT-*.md
```

## See Also

- [PRD README](../requirements/README.md) - Requirements that VPs validate
- [TDD README](../design/README.md) - Designs that VPs verify
- [CONVENTIONS.md](../CONVENTIONS.md) - Documentation standards
- [INDEX.md](../INDEX.md) - Cross-document references
