---
user-invocable: false
---

# Review Output Format Guide

This format is **recommended, not required**. Claude may adapt the structure based on:
- PR size and complexity
- Number of issues found
- User preferences expressed in the request

## Recommended Structure

```
Code Review: PR #{NUMBER} - {TITLE}

Author: {AUTHOR}
Branch: {HEAD} -> {BASE}
Files Changed: {COUNT} (+{ADDITIONS} -{DELETIONS})
Commits: {COUNT}

Review Summary:
{SUMMARY-PARAGRAPH}

---
BLOCKING ISSUES ({COUNT})
---

{If any blocking issues:}
1. {TITLE}
   Location: {FILE}:{LINE}
   Issue: {DESCRIPTION}
   Why: {IMPACT}
   Fix: {SUGGESTION}

{Repeat for each blocking issue}

---
STRONG SUGGESTIONS ({COUNT})
---

1. {TITLE}
   Location: {FILE}:{LINE}
   Issue: {DESCRIPTION}
   Why: {IMPACT}
   Fix: {SUGGESTION}

{Repeat for each suggestion}

---
NITS ({COUNT})
---

1. {TITLE}
   Location: {FILE}:{LINE}
   Suggestion: {DESCRIPTION}

{Repeat for nits}

---
POSITIVE FEEDBACK
---

- {WHAT-WAS-DONE-WELL-1}
- {WHAT-WAS-DONE-WELL-2}
- {WHAT-WAS-DONE-WELL-3}

---
QUESTIONS
---

1. {QUESTION-ABOUT-DESIGN-CHOICE}
2. {QUESTION-ABOUT-IMPLEMENTATION}

---
RECOMMENDATION
---

{APPROVE / REQUEST CHANGES / COMMENT}

{If REQUEST CHANGES:}
Must address {COUNT} blocking issues before approval.

{If APPROVE:}
Good to merge after addressing suggestions (optional).

{If COMMENT:}
Questions need clarification before decision.

---

Next Steps:
{If blocking:} Address blocking issues, then re-request review
{If suggestions:} Consider strong suggestions, iterate if needed
{If approved:} Merge when ready

Post review to PR:
  gh pr review {NUMBER} --comment --body "..."
  gh pr review {NUMBER} --approve --body "..."
  gh pr review {NUMBER} --request-changes --body "..."
```

## Adaptation Guidelines

**For small PRs (<100 lines)**:
- May combine sections if categories are empty
- Inline summary sufficient
- Skip empty categories entirely

**For large PRs (>500 lines)**:
- Consider per-file or per-component breakdown
- May use extended thinking for deeper analysis
- Group related issues by component

**When all issues are minor**:
- APPROVE recommendation with condensed nits section
- Focus positive feedback on architectural decisions
