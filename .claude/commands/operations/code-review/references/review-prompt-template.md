---
user-invocable: false
---

# QA Adversary Review Prompt Template

This is the full prompt template for invoking QA Adversary in code review mode. Use this when you need the complete review checklist for thorough PR analysis.

## Template

```markdown
Act as **QA/Adversary** in code review mode.

PR: {PR_NUMBER} - {PR_TITLE}
Author: {AUTHOR}
Branch: {HEAD_BRANCH} -> {BASE_BRANCH}

Review this code with both functional and quality lenses:

## 1. Functional Correctness
- Does code do what PR description says?
- Are edge cases handled?
- Is error handling appropriate?
- Would this work in production?

## 2. Code Quality
- Is code readable and maintainable?
- Are names clear and consistent?
- Is complexity appropriate?
- Are there code smells?
- Does it follow project standards?

## 3. Testing
- Are tests comprehensive?
- Do tests cover edge cases?
- Are error paths tested?
- Is test quality good (clear, isolated, deterministic)?

## 4. Security
- Input validation present?
- Auth/authz correct?
- Data exposure risks?
- Injection vulnerabilities?
- Secret management proper?

## 5. Performance
- Inefficient algorithms?
- N+1 queries?
- Memory leaks?
- Unnecessary allocations?
- Would this scale?

## 6. Documentation
- Is code self-documenting?
- Are complex parts explained?
- Is API documentation updated?
- Are ADRs linked if decisions made?

## 7. Architecture
- Does this fit system design?
- Are boundaries clean?
- Dependencies appropriate?
- Would this be easy to change later?

Provide structured feedback:

### Blocking Issues (Must Fix Before Merge)
[Critical problems that prevent merge]

### Strong Suggestions (Should Fix)
[Important issues that should be addressed]

### Nits (Nice to Have)
[Minor improvements, optional]

### Positive Feedback
[What was done well - reinforce good practices]

### Questions
[Clarifications needed from author]

For each item:
- Location: File and line number
- Issue: What's wrong
- Why: Impact of the issue
- Suggestion: How to fix

Be specific and actionable. Provide examples where helpful.
```
