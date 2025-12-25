# Playbook: New Feature Development

> Full lifecycle from requirements to pull request

## When to Use

- Adding new functionality to the system
- Feature request from stakeholder
- Planned roadmap item
- New component or service

## Prerequisites

- Clear feature description (even if rough)
- Stakeholder available for clarification
- Codebase access

## Command Sequence

### Phase 1: Initialize

```bash
/10x
```
**Expected output**: Team switched to 10x-dev-pack, roster displayed
**Decision point**: If complex feature, proceed. If trivial, consider `/hotfix` instead.

### Phase 2: Start Session

```bash
/start "Feature name" --complexity=MODULE
```
**Expected output**: Session created, Requirements Analyst invoked
**Decision point**: Adjust complexity level based on scope:
- SCRIPT: Single file, utility
- MODULE: Component, moderate
- SERVICE: APIs, infrastructure
- PLATFORM: Cross-cutting

### Phase 3: Requirements

Requirements Analyst produces PRD automatically after `/start`.

**Expected output**: PRD-{slug}.md created
**Decision point**: Review PRD with stakeholder if needed.

### Phase 4: Design (if MODULE+)

```bash
/architect
```
**Expected output**: TDD-{slug}.md and ADRs created
**Decision point**: Review architecture before proceeding.

### Phase 5: Implementation

```bash
/build
```
**Expected output**: Code and tests created
**Decision point**: If blocked, use `/handoff` to switch agents.

### Phase 6: Validation

```bash
/qa
```
**Expected output**: Test report, defects identified
**Decision point**: Fix defects before proceeding.

### Phase 7: Finalize

```bash
/wrap
```
**Expected output**: Session summary, quality gates checked

### Phase 8: Ship

```bash
/pr
```
**Expected output**: Pull request created with summary

## Variations

- **SCRIPT complexity**: Skip `/architect` phase
- **Cross-team feature**: Use `/handoff` between teams
- **Multi-task feature**: Use `/sprint` instead of `/task`

## Success Criteria

- [ ] PRD approved
- [ ] TDD complete (if MODULE+)
- [ ] Code passes tests
- [ ] QA sign-off
- [ ] PR created and ready for review

## Rollback

If things go wrong:
```bash
/park                          # Save state
# Address issues
/continue                      # Resume
```
