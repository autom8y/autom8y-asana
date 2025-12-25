# ADR Contribution Checklist

Version: 1.0
Last Updated: 2025-12-24

Use this checklist when creating or reviewing Architecture Decision Records (ADRs).

---

## For Authors: Pre-Submission Checklist

Before submitting an ADR for review, verify:

### Title & Naming
- [ ] Filename follows format: `ADR-{NNNN}-{kebab-case-title}.md`
- [ ] Number uses four digits with leading zeros (e.g., `0035`, `0145`)
- [ ] Title describes the decision, not the problem
- [ ] Title is specific and action-oriented
- [ ] Next available number is ADR-0145 (as of 2025-12-24)

### Metadata (10 points)
- [ ] Status field present (Proposed | Accepted | Deprecated | Superseded | Rejected)
- [ ] Author field present
- [ ] Date in ISO format (YYYY-MM-DD)
- [ ] Deciders field lists who was involved
- [ ] Related field cross-references PRD/TDD/ADR documents
- [ ] Format is bullet list (not table)

### Context (20 points)
- [ ] Situation explained (what is the current state?)
- [ ] Forces at play enumerated (what constraints are in tension?)
- [ ] Problem/question clearly stated (what triggered this decision?)
- [ ] Enough background for reader unfamiliar with project
- [ ] No assumptions about reader's knowledge

### Decision (15 points)
- [ ] Decision stated in one clear sentence
- [ ] Decision is unambiguous (no "probably" or "maybe")
- [ ] Code examples provided where applicable
- [ ] Concrete specifications included (not vague)
- [ ] Decision describes WHAT, not WHY (rationale comes next)

### Rationale (15 points)
- [ ] Explains WHY this decision over alternatives
- [ ] Addresses key trade-offs
- [ ] Provides specific reasons tied to forces in Context
- [ ] Uses numbered lists, tables, or subsections for clarity
- [ ] Avoids vague statements like "seems better"

### Alternatives Considered (20 points)
- [ ] At least 2 alternatives presented (excluding chosen decision)
- [ ] Each alternative has Description field
- [ ] Each alternative has Pros field
- [ ] Each alternative has Cons field
- [ ] Each alternative has "Why not chosen" field
- [ ] Alternatives are genuine options (not strawmen)
- [ ] Pros acknowledged even for rejected alternatives
- [ ] Rejection reasons are specific

### Consequences (10 points)
- [ ] Positive consequences listed
- [ ] Negative consequences listed (REQUIRED - no decision is perfect)
- [ ] Neutral consequences included if applicable
- [ ] Uses headings: `### Positive`, `### Negative`, `### Neutral`
- [ ] Consequences describe implications, not justifications
- [ ] Honest about costs, risks, and limitations

### Compliance (5 points)
- [ ] Enforcement mechanisms specified
- [ ] Includes at least one of: code review guidelines, tests, linting, CI checks
- [ ] Code locations referenced if applicable
- [ ] Documentation requirements specified if applicable
- [ ] Actionable (not just "developers should follow this")

### Overall Quality
- [ ] No section omitted
- [ ] Code examples use proper markdown fences with language hint
- [ ] Tables formatted with aligned pipes (if used)
- [ ] Cross-references valid (linked docs exist)
- [ ] No typos or grammar errors
- [ ] Total score estimate: ___/100 (target: 70+ for acceptance, 90+ for exemplary)

---

## For Reviewers: ADR Review Checklist

When reviewing an ADR submission, verify:

### Template Compliance
- [ ] All required sections present (Title, Metadata, Context, Decision, Rationale, Alternatives, Consequences, Compliance)
- [ ] Metadata uses bullet list format (not table)
- [ ] Alternatives use subsection format with all 4 fields
- [ ] Consequences use Positive/Negative/Neutral headings
- [ ] Follows canonical template structure

### Numbering & Naming
- [ ] ADR number is next in sequence (currently ADR-0145)
- [ ] No duplicate numbers exist
- [ ] Filename matches title
- [ ] Uses standard numbering (not ADR-SDK-XXX format)

### Content Quality
- [ ] Context explains problem clearly (can understand without external knowledge)
- [ ] Decision is unambiguous and specific
- [ ] Rationale explains WHY, not just WHAT
- [ ] Alternatives are genuine (not strawmen designed to make chosen option look good)
- [ ] Consequences are honest (includes negatives)
- [ ] Compliance mechanisms are actionable

### Technical Accuracy
- [ ] Decision is technically sound
- [ ] Code examples are correct and runnable
- [ ] Cross-references point to actual documents
- [ ] Terminology consistent with project glossary
- [ ] No conflicts with existing ADRs (unless superseding)

### Cross-References
- [ ] Related PRD/TDD/ADR links valid
- [ ] If superseding another ADR, old ADR updated with "Superseded by" link
- [ ] INDEX.md updated with new ADR in appropriate thematic section(s)
- [ ] INDEX.md updated with new ADR in "By Number" section

### Formatting
- [ ] Markdown syntax correct
- [ ] Code blocks use language hints (```python, ```bash, etc.)
- [ ] Tables aligned and readable
- [ ] No line length issues (paragraphs wrap naturally)
- [ ] Consistent heading levels

### Scoring Assessment

Use the rubric from STYLE-GUIDE.md:

| Section | Max Points | Score | Notes |
|---------|-----------|-------|-------|
| Title | 5 | ___ | |
| Metadata | 10 | ___ | |
| Context | 20 | ___ | |
| Decision | 15 | ___ | |
| Rationale | 15 | ___ | |
| Alternatives | 20 | ___ | |
| Consequences | 10 | ___ | |
| Compliance | 5 | ___ | |
| **TOTAL** | **100** | ___ | |

**Quality Tier**:
- 90-100: Exemplary ✓
- 70-89: Good (acceptable)
- 50-69: Adequate (request revisions)
- <50: Needs work (reject, provide feedback)

**Decision**:
- [ ] Approve (score >= 70)
- [ ] Request revisions (score 50-69)
- [ ] Reject (score < 50)

---

## Quality Gates

An ADR is ready for acceptance when:

### Minimum Requirements (All Must Pass)
- [ ] Score >= 70/100
- [ ] All required sections present
- [ ] At least 2 alternatives with complete structure
- [ ] Consequences include both positive AND negative
- [ ] Compliance mechanisms specified
- [ ] No broken cross-references
- [ ] No duplicate numbering

### Exemplary Criteria (90+ points)
- [ ] Context provides rich background
- [ ] Rationale uses comparison tables or multi-part structure
- [ ] 3+ alternatives with honest evaluation
- [ ] Consequences balanced and specific
- [ ] Code examples complete and runnable
- [ ] Compliance includes tests or automation

---

## Common Issues & Fixes

### Issue: Missing Negative Consequences

**Problem**: Consequences section only lists positive outcomes.

**Why This Matters**: Every decision has trade-offs. Omitting negatives suggests incomplete analysis or dishonesty.

**Fix**: Ask "What are we sacrificing with this decision?" Examples:
- Learning curve for new pattern
- Additional complexity
- Performance overhead
- Maintenance burden
- Scope limitations

---

### Issue: Strawman Alternatives

**Problem**: Alternatives are obviously bad choices designed to make the chosen option look good.

**Example**:
```markdown
### Alternative 1: Do Nothing
- **Pros**: No work
- **Cons**: Problem persists
- **Why not chosen**: Obviously won't work
```

**Why This Matters**: Defeats the purpose of ADRs - documenting genuine consideration of options.

**Fix**: Present realistic alternatives that could work, then explain specific trade-offs:
```markdown
### Alternative 1: Repository Pattern
- **Pros**: Familiar from SQLAlchemy, reduces boilerplate
- **Cons**: Requires model changes, hidden behavior
- **Why not chosen**: Violates explicit tracking requirement in PRD-0005
```

---

### Issue: Vague Rationale

**Problem**: Rationale doesn't explain WHY, just restates decision.

**Example**:
```markdown
## Rationale
This approach is better because it works well.
```

**Fix**: Provide specific reasons tied to forces in Context:
```markdown
## Rationale

1. **Developer Familiarity**: Mirrors SQLAlchemy/Django ORM patterns
2. **Explicit Scope**: Context manager provides clear batch boundaries
3. **Resource Cleanup**: Guarantees cleanup even on exceptions
```

---

### Issue: Incomplete Alternatives

**Problem**: Alternatives missing Description, Pros, Cons, or "Why not chosen".

**Fix**: Every alternative must have all 4 fields:
- **Description**: What this option entails
- **Pros**: Benefits (be honest, even for rejected options)
- **Cons**: Drawbacks
- **Why not chosen**: Specific reason for rejection

---

### Issue: No Compliance Mechanisms

**Problem**: Compliance section says "developers should follow this" without enforcement.

**Fix**: Specify actionable mechanisms:
- Code review guidelines
- Automated tests (unit, integration, architectural)
- Linting rules
- CI checks
- Documentation requirements
- Type hints and IDE support

---

### Issue: Ambiguous Decision

**Problem**: Decision uses vague language or presents multiple options.

**Example**:
```markdown
## Decision
We'll probably use SaveSession or maybe a transaction API.
```

**Fix**: State ONE clear decision:
```markdown
## Decision
Implement the Unit of Work pattern via a SaveSession class that acts as a context manager.
```

---

### Issue: Context Without Problem Statement

**Problem**: Context describes solution without explaining what problem it solves.

**Fix**: Always answer:
1. What is the current state?
2. What forces are in tension?
3. What specific problem/question triggered this decision?

---

## Reference Materials

### Study These Exemplary ADRs
- **ADR-0001**: Protocol-Based Extensibility (Score: 98/100)
  - 5 alternatives with full structure
  - Honest consequences
  - Actionable compliance

- **ADR-0035**: Unit of Work Pattern (Score: 100/100)
  - Forces clearly enumerated
  - Two-part rationale
  - Balanced consequences

- **ADR-0130**: Cache Population Location (Score: 100/100)
  - Effective use of comparison tables
  - Detailed compliance with code locations
  - Specific test requirements

### Documentation
- **Style Guide**: `/docs/decisions/STYLE-GUIDE.md` - comprehensive formatting and quality standards
- **Template**: `.claude/skills/documentation/templates/adr.md` - blank template
- **Index**: `/docs/decisions/INDEX.md` - thematic organization
- **Audit**: `/docs/audits/AUDIT-adr-quality-standardization.md` - quality assessment

---

## Workflow

### Author Workflow
1. Copy template from `.claude/skills/documentation/templates/adr.md`
2. Determine next ADR number (currently ADR-0145)
3. Fill all sections (don't skip Compliance or Consequences!)
4. Add code examples to make decision concrete
5. Self-review using "Pre-Submission Checklist" above
6. Self-score using rubric (target: 70+)
7. Submit for review

### Reviewer Workflow
1. Check template compliance
2. Verify numbering (no duplicates)
3. Assess content quality using "ADR Review Checklist"
4. Score using rubric (must be >= 70 for acceptance)
5. Check for common issues (strawmen, missing negatives, vague rationale)
6. Validate cross-references
7. Approve, request revisions, or reject with specific feedback

### Post-Acceptance
1. Author updates `/docs/decisions/INDEX.md`:
   - Add to appropriate thematic section(s)
   - Add to "By Number" section
   - Update "Supersession Chains" if applicable
2. If superseding an old ADR, update old ADR's Status field
3. Link from related PRD/TDD documents

---

## Scoring Quick Reference

| Score | Tier | Action |
|-------|------|--------|
| 90-100 | Exemplary | Approve - reference quality |
| 70-89 | Good | Approve - acceptable |
| 50-69 | Adequate | Request revisions |
| 0-49 | Needs Work | Reject with feedback |

**Minimum for acceptance**: 70/100

**Deductions**:
- Missing section: -10 to -20 points (depending on section weight)
- Strawman alternatives: -5 points per strawman
- No negative consequences: -4 points
- Vague rationale: -5 to -10 points
- Missing compliance: -5 points
- Incomplete alternatives: -2.5 points per missing field

---

## Tips for Quality

### For Authors

1. **Write Context First**: Understanding the problem helps clarify the decision
2. **Evaluate Alternatives Honestly**: Acknowledge pros even for rejected options
3. **Be Honest About Negatives**: Every decision has trade-offs
4. **Use Code Examples**: Make abstract decisions concrete
5. **Reference Related Docs**: Help readers find context (PRD/TDD/other ADRs)
6. **Think About Compliance**: How will this actually be enforced?

### For Reviewers

1. **Check for Strawmen**: Are alternatives realistic or designed to look bad?
2. **Verify Honesty**: Do consequences include negatives?
3. **Assess Rationale**: Does it explain WHY, not just WHAT?
4. **Validate Cross-Refs**: Do linked docs exist?
5. **Test Code Examples**: Are they runnable?
6. **Score Fairly**: Use rubric consistently

---

## Questions?

For questions about ADR contribution:
- **Format/Structure**: See `/docs/decisions/STYLE-GUIDE.md`
- **Examples**: Study ADR-0001, ADR-0035, ADR-0130
- **Template**: `.claude/skills/documentation/templates/adr.md`
- **Index**: `/docs/decisions/INDEX.md`

Contact doc-reviewer for clarification on review criteria.
