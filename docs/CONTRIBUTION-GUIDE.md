# Documentation Contribution Guide

Version: 1.0
Date: 2025-12-24
Author: Information Architect Agent

---

## Overview

This guide explains how to create, update, and maintain documentation in the autom8_asana project. Follow these conventions to ensure consistency and findability.

**Golden Rule**: INDEX.md status MUST match document frontmatter status. Status divergence is a documentation bug.

---

## Where Does New Documentation Go?

Use this decision tree:

```
What are you documenting?
│
├─ Product requirements (WHAT and WHY)
│  └─ → /docs/requirements/PRD-FEATURE-NAME.md
│
├─ Technical design (HOW)
│  └─ → /docs/design/TDD-FEATURE-NAME.md
│
├─ Architectural decision (WHY we chose this approach)
│  └─ → /docs/decisions/ADR-NNNN-decision-name.md
│
├─ Test strategy
│  └─ → /docs/testing/TP-NNNN-feature-name.md
│
├─ Reference data (entity types, fields, algorithms)
│  └─ → /docs/reference/REF-topic-name.md
│
├─ Operational troubleshooting
│  └─ → /docs/runbooks/RUNBOOK-system-issue.md
│
├─ User guide or tutorial
│  └─ → /docs/guides/topic.md
│
├─ Discovery or analysis
│  └─ → /docs/analysis/DISCOVERY-topic.md or GAP-ANALYSIS-topic.md
│
├─ Initiative coordination
│  └─ → /docs/initiatives/PROMPT-0-INITIATIVE-NAME.md
│
└─ Sprint planning
   └─ → /docs/planning/sprints/PRD-SPRINT-N-description.md
```

**If still unsure**: Ask in #engineering or consult [INDEX.md](INDEX.md) for examples.

---

## Naming Your Document

### Naming Conventions

| Document Type | Pattern | Example |
|---------------|---------|---------|
| PRD (named) | `PRD-FEATURE-NAME.md` | `PRD-CACHE-INTEGRATION.md` |
| PRD (numbered) | `PRD-NNNN-feature-name.md` | `PRD-0001-sdk-extraction.md` |
| TDD (named) | `TDD-FEATURE-NAME.md` | `TDD-CACHE-INTEGRATION.md` |
| TDD (numbered) | `TDD-NNNN-feature-name.md` | `TDD-0001-sdk-architecture.md` |
| ADR | `ADR-NNNN-decision-name.md` | `ADR-0135-new-decision.md` |
| Test Plan | `TP-NNNN-feature-name.md` | `TP-0010-new-feature.md` |
| Reference | `REF-topic-name.md` | `REF-cache-staleness-detection.md` |
| Runbook | `RUNBOOK-system-issue.md` | `RUNBOOK-cache-troubleshooting.md` |
| Guide | `descriptive-name.md` | `quickstart.md` |

**Case Convention**: All lowercase with hyphens (kebab-case)

**Numbered vs. Named**:
- **Numbered** (legacy): Used for sequential allocation. Preserves git history.
- **Named** (preferred): Descriptive, searchable, self-documenting.

**For new PRDs and TDDs**: Use named format (e.g., `PRD-FEATURE-NAME.md`)
**For new ADRs**: Use numbered format (next = ADR-0135)
**For new Test Plans**: Use numbered format (next = TP-0010)

---

## Required Frontmatter

All formal documents (PRDs, TDDs, ADRs, TPs) MUST include frontmatter:

```yaml
---
status: <Status Value>       # See status values below
created: YYYY-MM-DD          # Initial creation date
updated: YYYY-MM-DD          # Last significant update
pr: <PR URL>                 # (optional) Implementing PR
superseded_by: <Doc Link>    # (if Superseded) Link to replacement
decision: <ADR Link>         # (if Rejected/NO-GO) Link to decision
---
```

### Status Values

#### For PRDs and TDDs:
- `Draft` - Initial authoring, not yet reviewed
- `In Review` - Under stakeholder review
- `Approved` - Approved for implementation
- `Active` - Currently being implemented
- `Implemented` - Code in production, feature live
- `Superseded` - Replaced by different approach (MUST include `superseded_by:` link)
- `Rejected` - Decided not to implement (MUST include `decision:` link)

**TDDs only**:
- `NO-GO` - Design explicitly rejected (e.g., TDD-0026-crud-base-class)

#### For Test Plans:
- `Draft` - Test plan being written
- `Approved` - Test plan approved
- `PASS` - Tests passed
- `FAIL` - Tests failed

#### For Validation Reports:
- `PASS` - Validation passed
- `FAIL` - Validation failed
- `APPROVED` - Feature approved for production

**Critical Rule**: `status:` in document frontmatter MUST match `Status` column in INDEX.md

---

## Creating a New PRD

1. **Check for existing PRD**: Search [INDEX.md](INDEX.md) to avoid duplication
2. **Copy template**: Use existing PRD (e.g., `PRD-CACHE-INTEGRATION.md`) as template
3. **Name the file**: Use `PRD-FEATURE-NAME.md` format
4. **Fill frontmatter**:
   ```yaml
   ---
   status: Draft
   created: 2025-12-24
   updated: 2025-12-24
   ---
   ```
5. **Write sections**:
   - Problem Statement - What problem are we solving?
   - Solution - High-level solution approach
   - Requirements - Detailed functional requirements
   - Success Criteria - How do we know it's done?
   - Non-Goals - What are we explicitly NOT doing?
6. **Add to INDEX.md**:
   ```markdown
   | [PRD-FEATURE-NAME](requirements/PRD-FEATURE-NAME.md) | Feature Name | Draft |
   ```
7. **Create TDD**: Create corresponding `TDD-FEATURE-NAME.md` in `/docs/design/`
8. **Update INDEX.md TDD section**: Link PRD and TDD

---

## Creating a New TDD

1. **Verify PRD exists**: Every TDD should have a corresponding PRD
2. **Copy template**: Use existing TDD (e.g., `TDD-CACHE-INTEGRATION.md`)
3. **Name the file**: Use `TDD-FEATURE-NAME.md` (match PRD name)
4. **Fill frontmatter**: Same as PRD
5. **Write sections**:
   - Architecture Overview - High-level design
   - Components - Key components and responsibilities
   - Interfaces - APIs and protocols
   - Data Structures - Models and schemas
   - Error Handling - Failure modes and recovery
   - Testing Strategy - How to test this design
6. **Add to INDEX.md**:
   ```markdown
   | [TDD-FEATURE-NAME](design/TDD-FEATURE-NAME.md) | Feature Name | PRD-FEATURE-NAME | Draft |
   ```

---

## Creating a New ADR

ADRs use numbered format. Next available: **ADR-0135**

1. **Verify decision significance**: ADRs are for significant, lasting decisions
2. **Copy template**: Use existing ADR (e.g., `ADR-0123-cache-provider-selection.md`)
3. **Name the file**: `ADR-0135-decision-name.md` (use next number)
4. **Write sections**:
   - Context - What decision needs to be made?
   - Decision - What did we decide?
   - Rationale - Why did we choose this?
   - Consequences - What are the implications?
   - Alternatives Considered - What else did we evaluate?
5. **Add to INDEX.md**: Add to ADRs by Topic section
6. **Increment next number**: Update "Document Number Allocation" section

**ADRs are immutable**: Once published, ADRs are not edited. If decision changes, create new ADR referencing the old one.

---

## Creating a New Reference Doc

Reference docs consolidate duplicated content. Create when 3+ PRDs/TDDs explain the same concept.

1. **Identify duplication**: Find 3+ docs explaining same concept
2. **Name the file**: `REF-topic-name.md`
3. **Extract content**: Pull common explanation from source docs
4. **Write comprehensive version**: Single authoritative source
5. **Update source docs**: Replace duplicated explanation with link:
   ```markdown
   For [topic] details, see [REF-topic-name](../reference/REF-topic-name.md).
   ```
6. **Add to INDEX.md**: Add to Reference Data section
7. **Update reference/README.md**: Add to reference docs list

---

## Creating a New Runbook

Runbooks are for operational troubleshooting.

1. **Identify recurring issue**: Should be production issue that recurs
2. **Name the file**: `RUNBOOK-system-issue.md`
3. **Write sections**:
   - Problem Statement - What is failing?
   - Symptoms - How do you know it's this problem?
   - Investigation Steps - How to diagnose
   - Resolution - How to fix
   - Prevention - How to prevent recurrence
4. **Test the runbook**: Verify steps work during next incident
5. **Add to INDEX.md**: Add to Runbooks section
6. **Update runbooks/README.md**: Add to runbooks list

---

## Updating Existing Documentation

### Updating Document Status

When feature status changes (e.g., Draft → Active → Implemented):

1. **Update document frontmatter**:
   ```yaml
   ---
   status: Implemented
   updated: 2025-12-24
   pr: https://github.com/org/repo/pull/123
   ---
   ```

2. **Update INDEX.md**: Change Status column to match

3. **Verify sync**: Ensure frontmatter status = INDEX.md status

**Trigger for updates**:
- Code merged to main → Update to `Implemented`
- Work started → Update to `Active`
- Approved by stakeholders → Update to `Approved`
- Different approach chosen → Update to `Superseded`, add `superseded_by:` link

### Adding Supersession Notice

When a document is superseded:

1. **Update frontmatter**:
   ```yaml
   ---
   status: Superseded
   superseded_by: ../decisions/ADR-0101-replacement.md
   ---
   ```

2. **Add notice at top of document** (after frontmatter):
   ```markdown
   > **SUPERSEDED**
   >
   > This document has been superseded by [replacement](../decisions/ADR-0101-replacement.md).
   >
   > Preserved for historical context. Do not implement.
   ```

3. **Update INDEX.md**: Change status to `Superseded`

### Adding Rejection Notice

When a proposal is rejected:

1. **Update frontmatter**:
   ```yaml
   ---
   status: Rejected
   decision: ../decisions/ADR-0135-rejection-rationale.md
   ---
   ```

2. **Add notice at top of document**:
   ```markdown
   > **REJECTED**
   >
   > This proposal has been rejected. See [decision](../decisions/ADR-0135-rejection-rationale.md) for rationale.
   >
   > Preserved for historical context. Do not implement.
   ```

3. **Update INDEX.md**: Change status to `Rejected`

---

## Cross-Referencing Other Documents

### Inline Links

Use for critical context:

```markdown
See [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md) for requirements.
```

**Relative paths**: Always use relative paths (not absolute)

**Path examples**:
- From PRD to TDD: `../design/TDD-FEATURE-NAME.md`
- From TDD to PRD: `../requirements/PRD-FEATURE-NAME.md`
- From PRD to ADR: `../decisions/ADR-0123-decision.md`
- From PRD to Reference: `../reference/REF-topic.md`

### See Also Sections

Use at end of document for related docs:

```markdown
## Related Documentation

- **Requirements**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md)
- **Architecture**: [ADR-0123-cache-provider-selection](../decisions/ADR-0123-cache-provider-selection.md)
- **Reference**: [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md)
- **Operations**: [RUNBOOK-cache-troubleshooting](../runbooks/RUNBOOK-cache-troubleshooting.md)
```

---

## Updating INDEX.md

INDEX.md is the **central registry** and **source of truth** for documentation status.

### Adding a New Document

1. **Find appropriate section**: PRDs, TDDs, ADRs, etc.
2. **Add entry** in table format:
   ```markdown
   | [PRD-FEATURE-NAME](requirements/PRD-FEATURE-NAME.md) | Feature Name | Draft |
   ```
3. **For TDDs**: Include paired PRD:
   ```markdown
   | [TDD-FEATURE-NAME](design/TDD-FEATURE-NAME.md) | Feature Name | PRD-FEATURE-NAME | Draft |
   ```
4. **Update "Last Updated"** at top of INDEX.md

### Updating Document Status in INDEX.md

1. **Find document entry** in INDEX.md
2. **Update Status column** to match document frontmatter
3. **Verify match**: Status in INDEX.md = status in document frontmatter

**Weekly verification**: Run validation script (if available) to check for divergence

---

## Archiving Completed Work

### When to Archive

| Content Type | Archive When | Destination |
|--------------|--------------|-------------|
| PROMPT-0 files | Initiative status = "Complete" | `.archive/initiatives/YYYY-QN/` |
| Sprint planning docs | 2 weeks after sprint end | `.archive/planning/YYYY-QN-sprints/` |
| Discovery docs | 1 year after creation, if unreferenced | `.archive/discovery/` |
| Validation reports | 1 year after creation | `.archive/validation/` |
| Superseded PRDs/TDDs | **NEVER** - keep in place with notice | N/A |

**Why keep superseded PRDs/TDDs?**: They provide historical context for decisions. Archiving loses git blame and discoverability.

### Archiving Process

1. **Create archive directory** (if not exists):
   ```bash
   mkdir -p docs/.archive/initiatives/2025-Q4
   ```

2. **Move file** (preserve git history):
   ```bash
   git mv docs/initiatives/PROMPT-0-FEATURE.md docs/.archive/initiatives/2025-Q4/
   ```

3. **Update INDEX.md**: Either update path or remove from active section, add to Archived Content

4. **Commit**:
   ```bash
   git add -A
   git commit -m "docs: Archive completed initiative PROMPT-0-FEATURE"
   ```

---

## Review Process

### Before Committing

Checklist:
- [ ] Document has required frontmatter (status, created, updated)
- [ ] Document added to INDEX.md in appropriate section
- [ ] Status in INDEX.md matches status in document frontmatter
- [ ] Cross-references use relative paths
- [ ] If superseded/rejected, prominent notice added
- [ ] If PRD, corresponding TDD exists or is planned
- [ ] If reference doc, source PRDs updated to link instead of duplicate

### PR Review

Documentation PRs should be reviewed for:
- Accuracy (does it match implementation?)
- Completeness (are all sections filled?)
- Consistency (does it follow conventions?)
- Status accuracy (does status reflect reality?)

**Reviewers**: Tech Writer, Lead Engineer, or Doc Reviewer agent

---

## Common Patterns

### Pattern: Creating a Feature with PRD + TDD

1. Create PRD with `status: Draft`
2. Create TDD with `status: Draft`
3. Add both to INDEX.md with `Draft` status
4. Get stakeholder approval → Update both to `Approved`
5. Start implementation → Update both to `Active`
6. Merge code → Update both to `Implemented`, add `pr:` link

### Pattern: Rejecting a Proposal

1. Create ADR documenting rejection decision
2. Update PRD frontmatter: `status: Rejected`, `decision: ../decisions/ADR-NNNN.md`
3. Add rejection notice to top of PRD
4. Update INDEX.md status to `Rejected`

### Pattern: Superseding an Approach

1. Create new PRD/TDD for replacement approach
2. Create ADR explaining why approach changed
3. Update old PRD frontmatter: `status: Superseded`, `superseded_by: ../requirements/PRD-NEW.md`
4. Add supersession notice to top of old PRD
5. Update INDEX.md status to `Superseded`

### Pattern: Extracting to Reference Doc

1. Identify 3+ PRDs duplicating same explanation
2. Create `REF-topic.md` with comprehensive version
3. Update each source PRD to replace explanation with link:
   ```markdown
   For [topic] details, see [REF-topic](../reference/REF-topic.md).
   ```
4. Add REF doc to INDEX.md Reference Data section

---

## Tools and Validation

### Markdown Validation

Use markdown linter to check formatting:
```bash
markdownlint docs/**/*.md
```

### Link Validation

Check for broken links:
```bash
markdown-link-check docs/**/*.md
```

### Status Validation

Verify INDEX.md status matches frontmatter (if script available):
```bash
./scripts/validate-doc-status.sh
```

---

## Getting Help

| Question | Where to Ask |
|----------|--------------|
| Where does this doc go? | This guide (decision tree above) |
| What's the right status value? | This guide (status values section) |
| How do I name this doc? | This guide (naming conventions) |
| Is there already a doc for this? | Search [INDEX.md](INDEX.md) |
| Should this be a PRD or TDD? | #engineering channel |
| Should I create a reference doc? | #engineering channel |

---

## Examples

### Example: New Cache Feature

1. **Create PRD**: `docs/requirements/PRD-CACHE-BATCH-OPERATIONS.md`
   ```yaml
   ---
   status: Draft
   created: 2025-12-24
   updated: 2025-12-24
   ---
   ```

2. **Create TDD**: `docs/design/TDD-CACHE-BATCH-OPERATIONS.md`
   ```yaml
   ---
   status: Draft
   created: 2025-12-24
   updated: 2025-12-24
   ---
   ```

3. **Update INDEX.md**:
   ```markdown
   | [PRD-CACHE-BATCH-OPERATIONS](requirements/PRD-CACHE-BATCH-OPERATIONS.md) | Cache Batch Operations | Draft |
   ```
   ```markdown
   | [TDD-CACHE-BATCH-OPERATIONS](design/TDD-CACHE-BATCH-OPERATIONS.md) | Cache Batch Operations | PRD-CACHE-BATCH-OPERATIONS | Draft |
   ```

4. **After approval**: Update both to `status: Approved` in frontmatter and INDEX.md

5. **After implementation**: Update both to `status: Implemented`, add `pr:` link

### Example: Creating a Runbook

1. **Create runbook**: `docs/runbooks/RUNBOOK-redis-connection-failures.md`
   ```markdown
   # Redis Connection Failures Runbook

   ## Problem Statement
   Redis connection failures causing cache unavailability

   ## Symptoms
   - Logs show "Connection refused" errors
   - Cache operations failing
   - Fallback to API working

   ## Investigation Steps
   1. Check Redis server status
   2. Verify network connectivity
   3. Check authentication credentials

   ## Resolution
   [Resolution steps...]

   ## Prevention
   [Prevention measures...]
   ```

2. **Update runbooks/README.md**:
   ```markdown
   | [RUNBOOK-redis-connection-failures.md](RUNBOOK-redis-connection-failures.md) | Redis | Connection failures |
   ```

3. **Update INDEX.md** (if Runbooks section exists):
   ```markdown
   | [RUNBOOK-redis-connection-failures.md](runbooks/RUNBOOK-redis-connection-failures.md) | Redis | Connection failures |
   ```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-24 | Initial contribution guide based on IA spec |
