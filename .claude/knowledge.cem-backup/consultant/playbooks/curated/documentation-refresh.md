# Playbook: Documentation Refresh

> Update and improve project documentation

## When to Use

- Documentation is stale
- New features lack docs
- Onboarding is difficult
- API changes need reflecting
- README needs updating

## Prerequisites

- Understanding of what needs documenting
- Access to code for reference

## Command Sequence

### Phase 1: Switch to Doc Team

```bash
/docs
```
**Expected output**: Team switched to doc-team-pack

### Phase 2: Start Documentation Session

```bash
/start "Document [area]" --complexity=SECTION
```
**Expected output**: Session created, documentation-analyst invoked
**Decision point**: Complexity levels:
- PAGE: Single doc page
- SECTION: Related pages
- SITE: Full documentation

### Phase 3: Scoping

Documentation Analyst assesses needs.

**Expected output**: Documentation plan with gaps identified

### Phase 4: Drafting

Technical Writer creates content.

**Expected output**: Draft documentation

### Phase 5: Editing

Editor refines and polishes.

**Expected output**: Polished content ready for review

### Phase 6: Review

**Decision point**: Get stakeholder feedback if needed.

### Phase 7: Publishing

Publisher finalizes documentation.

**Expected output**: Published, accessible docs

### Phase 8: Wrap Up

```bash
/wrap
```
**Expected output**: Session summary

## Variations

- **README only**: Quick update, may not need full workflow
- **API docs**: Focus on technical accuracy
- **User guides**: Focus on clarity and examples
- **Architecture docs**: May need `/10x` for TDD format

## Success Criteria

- [ ] Documentation gaps identified
- [ ] Content drafted
- [ ] Content reviewed and edited
- [ ] Documentation published
- [ ] Links verified working

## Quick Path

For simple README updates:
```bash
/docs
/task "Update README installation section" --complexity=PAGE
```
