# Documentation Workflow & Lifecycle

## Workflow Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WORKFLOW PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   REQUIREMENTS   │     │    ARCHITECT     │     │    ENGINEER      │     │   QA/ADVERSARY   │
│     ANALYST      │     │                  │     │                  │     │                  │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │                        │
         │  ┌─────────────────┐   │                        │                        │
         ├──│ Produce PRD     │   │                        │                        │
         │  └────────┬────────┘   │                        │                        │
         │           │            │                        │                        │
         │           ▼            │                        │                        │
         │  ┌─────────────────┐   │                        │                        │
         │  │ PRD Review      │◄──┼── Clarifying questions │                        │
         │  └────────┬────────┘   │                        │                        │
         │           │            │                        │                        │
         │           ▼            │                        │                        │
         │  ┌─────────────────┐   │                        │                        │
         └──│ PRD Approved    │───┼──► Handoff             │                        │
            └─────────────────┘   │                        │                        │
                                  │  ┌─────────────────┐   │                        │
                                  ├──│ Check existing  │   │                        │
                                  │  │ ADRs & TDDs     │   │                        │
                                  │  └────────┬────────┘   │                        │
                                  │           │            │                        │
                                  │           ▼            │                        │
                                  │  ┌─────────────────┐   │                        │
                                  ├──│ Produce TDD     │   │                        │
                                  │  │ Reference ADRs  │   │                        │
                                  │  └────────┬────────┘   │                        │
                                  │           │            │                        │
                                  │           ▼            │                        │
                                  │  ┌─────────────────┐   │                        │
                                  │  │ New decisions?  │   │                        │
                                  │  │ Write ADRs      │   │                        │
                                  │  └────────┬────────┘   │                        │
                                  │           │            │                        │
                                  │           ▼            │                        │
                                  │  ┌─────────────────┐   │                        │
                                  └──│ TDD Approved    │───┼──► Handoff             │
                                     └─────────────────┘   │                        │
                                                           │  ┌─────────────────┐   │
                                                           ├──│ Implement per   │   │
                                                           │  │ TDD             │   │
                                                           │  └────────┬────────┘   │
                                                           │           │            │
                                                           │           ▼            │
                                                           │  ┌─────────────────┐   │
                                                           │  │ Impl decisions? │   │
                                                           │  │ Write ADRs      │   │
                                                           │  └────────┬────────┘   │
                                                           │           │            │
                                                           │           ▼            │
                                                           │  ┌─────────────────┐   │
                                                           └──│ Code Complete   │───┼──► Handoff
                                                              └─────────────────┘   │
                                                                                    │  ┌─────────────────┐
                                                                                    ├──│ Produce Test    │
                                                                                    │  │ Plan from PRD   │
                                                                                    │  └────────┬────────┘
                                                                                    │           │
                                                                                    │           ▼
                                                                                    │  ┌─────────────────┐
                                                                                    ├──│ Execute Tests   │
                                                                                    │  └────────┬────────┘
                                                                                    │           │
                                                                                    │           ▼
                                                                                    │  ┌─────────────────┐
                                                                                    │  │ Pass?           │
                                                                                    │  └────────┬────────┘
                                                                                    │           │
                                                                          ┌────────┼───────────┴───────────┐
                                                                          │        │                       │
                                                                          ▼        │                       ▼
                                                                   ┌──────────┐    │              ┌──────────────┐
                                                                   │ APPROVED │    │              │ FAIL: Route  │
                                                                   │ Ship it  │    │              │ to Engineer  │
                                                                   └──────────┘    │              │ or Analyst   │
                                                                                   │              └──────────────┘
                                                                                   │                       │
                                                                                   │◄──────────────────────┘
                                                                                   │       (iterate)
```

---

## Document Lifecycle

### Status Progression

```
Draft → In Review → Approved → [Active] → Deprecated/Superseded
```

### When to Update vs. Create New

| Situation                                 | Action                                       |
| ----------------------------------------- | -------------------------------------------- |
| Minor clarification or typo               | Update in place, note in revision history    |
| Scope change within same feature          | Update existing doc, increment version       |
| Significant pivot or new direction        | Supersede old doc, create new with reference |
| New feature building on existing patterns | Reference existing ADRs, create new PRD/TDD  |
| Changing a previous decision              | Create new ADR that supersedes the old one   |

### Checking for Existing Documentation

Before creating any document, agents MUST:

1. **Search existing docs** in the canonical locations
2. **Check related documents** linked in PRDs/TDDs/ADRs
3. **Ask**: Does this decision/requirement/design already exist somewhere?

If existing documentation is found:
- **Still valid?** Reference it
- **Needs update?** Propose amendments
- **Obsolete?** Mark as deprecated, create new

---

## Document Indexing

Maintain an index at `/docs/INDEX.md`:

```markdown
# Documentation Index

## PRDs
| ID       | Title               | Status   | Date       |
| -------- | ------------------- | -------- | ---------- |
| PRD-0001 | User Authentication | Approved | 2024-01-15 |

## TDDs
| ID       | Title               | PRD      | Status   | Date       |
| -------- | ------------------- | -------- | -------- | ---------- |
| TDD-0001 | Auth Service Design | PRD-0001 | Approved | 2024-01-18 |

## ADRs
| ID       | Title                              | Status   | Date       |
| -------- | ---------------------------------- | -------- | ---------- |
| ADR-0001 | Use JWT for session tokens         | Accepted | 2024-01-17 |
| ADR-0002 | Repository pattern for data access | Accepted | 2024-01-10 |

## Test Plans
| ID      | Title              | PRD      | TDD      | Status   |
| ------- | ------------------ | -------- | -------- | -------- |
| TP-0001 | Auth Service Tests | PRD-0001 | TDD-0001 | Approved |
```

---

## Cross-Agent Coordination

Each agent follows these documentation protocols:

### Before Creating Documentation

1. Check `/docs/INDEX.md` for existing relevant documents
2. Search `/docs/{decisions,design,requirements}/` for related content
3. Reference existing ADRs rather than re-explaining decisions
4. Link to existing TDDs for established patterns

### When Creating Documentation

1. Use the canonical templates exactly
2. Assign the next sequential ID
3. Update `/docs/INDEX.md`
4. Link to all related documents

### When Existing Documentation Applies

1. Reference by ID (e.g., "Per ADR-0042...")
2. Do not duplicate content
3. If updates needed, propose amendments with rationale
