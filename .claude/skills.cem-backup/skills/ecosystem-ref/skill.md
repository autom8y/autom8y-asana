---
name: ecosystem-ref
description: "Ecosystem infrastructure workflow coordination. Use when: debugging CEM/skeleton/roster, designing hooks/skills, migrating satellites, validating cross-project compatibility. Triggers: ecosystem, CEM, skeleton, roster, sync, hook, skill, satellite, migration, compatibility."
---

# Ecosystem Infrastructure Workflow

> **Status**: Active

## Protocol Overview

The ecosystem-pack maintains foundational infrastructure enabling Claude Code's multi-project context system. This workflow achieves reliability through systematic diagnosis, design, implementation, documentation, and validation:

- **Root cause analysis** - Issues traced to specific CEM/skeleton/roster components
- **Backward compatibility** - Migrations planned with clear upgrade paths
- **Satellite validation** - Changes tested across project matrix before rollout
- **Infrastructure-first** - No feature creep; builds enablers, not features
- **Migration runbooks** - Breaking changes documented before implementation

---

## Agent Routing

### Quick Reference

| Agent | Domain Authority | Primary Artifact |
|-------|------------------|------------------|
| **Ecosystem Analyst** | Diagnose ecosystem problems, map scope, identify root causes | Gap Analysis |
| **Context Architect** | Design context solutions (hooks, skills, settings schema, CEM behavior) | Context Design, Hook/Skill Schema |
| **Integration Engineer** | Implement CEM changes, skeleton updates, roster modifications | Working implementation, integration tests |
| **Documentation Engineer** | Document migration paths, compatibility matrices, ecosystem changes | Migration Runbook, API documentation |
| **Compatibility Tester** | Validate across satellite matrix, verify upgrade paths work | Compatibility Report, defect reports |

### When to Route

**By Signal**:

| Request | Likely Agent |
|---------|--------------|
| "Sync is failing with conflicts" | Ecosystem Analyst |
| "How should we implement this hook?" | Context Architect |
| "Build it" | Integration Engineer |
| "Document the upgrade path" | Documentation Engineer |
| "Does it work across satellites?" | Compatibility Tester |

**By Complexity**:

| Complexity | Typical Pattern | Example |
|------------|-----------------|---------|
| PATCH | Analyst -> Engineer -> Tester | Fix CEM sync bug in conflict detection |
| MODULE | Analyst -> Architect -> Engineer -> Docs -> Tester | Add new hook lifecycle event to skeleton |
| SYSTEM | Full 5-agent workflow | Redesign settings merge to support 3-tier architecture |
| MIGRATION | Extended workflow with full satellite validation | Deprecate old hook format, migrate all satellites |

---

## Workflow Phases

### 1. Analysis (Ecosystem Analyst)

**Goal**: Trace issue to specific component, define success criteria

- Reproduce issue or scope new capability
- Identify which system(s) affected (CEM/skeleton/roster)
- Trace root cause to specific component
- Define success criteria (e.g., "sync completes without conflicts")

**Handoff criteria**:
- [ ] Root cause identified to specific component (not vague "sync broken")
- [ ] Success criteria defined with measurable outcomes
- [ ] Affected systems enumerated (CEM? skeleton? roster? all three?)
- [ ] Gap Analysis document exists with reproduction steps

### 2. Design (Context Architect)

**Goal**: Design solution architecture, plan backward compatibility

- Design solution architecture
- Define hook/skill schemas if introducing new patterns
- Specify settings changes or CEM behavior modifications
- Plan backward compatibility strategy

**Handoff criteria**:
- [ ] Solution architecture documented in Context Design
- [ ] Hook/Skill Schema defined if introducing new patterns
- [ ] Backward compatibility strategy specified (or "breaking change" declared)
- [ ] Settings schema changes documented
- [ ] Integration test strategy outlined (what satellites to test against)

### 3. Implementation (Integration Engineer)

**Goal**: Modify CEM/skeleton/roster code, ensure satellite integration works

- Modify CEM/skeleton/roster code
- Update schemas and templates
- Write integration tests (verify satellite integration, not just unit tests)
- Ensure changes work in skeleton first

**Handoff criteria**:
- [ ] Implementation complete and committed
- [ ] Integration tests pass (verified sync works with test satellites)
- [ ] Schema files updated (if applicable)
- [ ] Breaking changes list compiled
- [ ] No "TODO" or "FIXME" comments in critical paths

### 4. Documentation (Documentation Engineer)

**Goal**: Document migration paths, enable smooth satellite upgrades

- Write migration runbooks for breaking changes
- Update compatibility matrices
- Document new APIs or schema changes
- Create rollout instructions for satellite updates

**Handoff criteria**:
- [ ] Migration runbook exists for breaking changes (or N/A for backward-compatible)
- [ ] API documentation updated for new/changed interfaces
- [ ] Compatibility matrix draft prepared with expected outcomes
- [ ] Rollout instructions clear enough for satellite owners to execute
- [ ] All new schemas/hooks/skills documented in roster

### 5. Validation (Compatibility Tester)

**Goal**: Verify changes work across satellite matrix, validate migration runbooks

- Test against satellite matrix (minimal, standard, complex satellites)
- Verify `cem sync` succeeds across all test cases
- Validate migration runbooks actually work (run them, don't just read)
- Confirm no regressions in existing satellites

**Completion criteria**:
- [ ] All complexity-appropriate satellites tested (PATCH=1, MODULE=3, SYSTEM=5, MIGRATION=all)
- [ ] `cem sync` succeeds for all test cases
- [ ] Migration runbook validated (actually run it, don't just read it)
- [ ] Compatibility Report published with test results
- [ ] No P0/P1 defects open (P2+ can defer to backlog)
- [ ] Rollout plan approved (MIGRATION only)

---

## Quality Gates Summary

Quality gates are mandatory checkpoints between phases:

- **Gap Analysis**: Root cause identified to specific component, success criteria defined, affected systems enumerated
- **Context Design**: Solution architecture documented, backward compatibility planned, integration test strategy defined
- **Implementation**: Code complete, integration tests pass, schemas updated, breaking changes listed
- **Migration Runbook**: Breaking changes documented, compatibility matrix updated, rollout instructions clear
- **Compatibility Report**: Satellite matrix tested, `cem sync` succeeds, migration runbooks validated

---

## Complexity Levels

| Level | Scope | Phases | Quality Gates |
|-------|-------|--------|---------------|
| **PATCH** | Single file change, no schema impact | Analysis → Implementation → Validation | Gap Analysis, Compatibility Report; 1 test case, skeleton only |
| **MODULE** | Single system (CEM or skeleton or roster) | Analysis → Design → Implementation → Documentation → Validation | + Context Design, Migration Runbook; 3 test cases, skeleton + 2 satellites |
| **SYSTEM** | Multi-system change | All phases | + ADR, Hook/Skill Schema; 5 test cases, skeleton + 4 diverse satellites |
| **MIGRATION** | Cross-satellite rollout | All phases + extended validation | + Rollout Plan, Communication; Full suite, all registered satellites |

---

## Command Reference

### Primary Commands

- **`/ecosystem`** - Full pipeline (all agents, all phases, complexity auto-detected)
- **`/ecosystem-analyze`** - Ecosystem Analyst only (diagnose issues, scope work)
- **`/ecosystem-design`** - Context Architect only (design hooks/skills/CEM behavior)
- **`/ecosystem-implement`** - Integration Engineer only (code CEM/skeleton/roster changes)
- **`/ecosystem-document`** - Documentation Engineer only (write migration runbooks)
- **`/ecosystem-validate`** - Compatibility Tester only (test satellite matrix)

### Specialized Commands

- **`/cem-debug`** - Ecosystem Analyst with CEM diagnostic focus
- **`/hook-design`** - Context Architect for new hook patterns
- **`/skill-design`** - Context Architect for new skill patterns
- **`/satellite-scaffold`** - Integration Engineer for new satellite setup
- **`/migration-plan`** - Documentation Engineer for breaking change rollouts

### Complexity Modifiers

All commands accept `--complexity=[PATCH|MODULE|SYSTEM|MIGRATION]` to override auto-detection.

---

## Key Differences from 10x Development Workflow

| Aspect | 10x-dev-pack | ecosystem-pack |
|--------|--------------|----------------|
| **Entry artifact** | PRD (user requirements) | Gap Analysis (diagnostic report) |
| **Design output** | TDD (technical design) | Context Design (hook/skill/schema design) |
| **Implementation focus** | Feature code | Infrastructure code (CEM/skeleton/roster) |
| **Documentation phase** | Optional (ADRs inline) | Required for MODULE+ (migration runbooks) |
| **Validation artifact** | Test Plan (feature tests) | Compatibility Report (satellite matrix) |
| **Success criteria** | Feature works in project | Feature works across all satellites |
| **Complexity levels** | SCRIPT/MODULE/SERVICE/PLATFORM | PATCH/MODULE/SYSTEM/MIGRATION |

---

## Success Criteria

Ecosystem infrastructure changes succeed when:

- [ ] CEM sync completes without conflicts across all test satellites
- [ ] Skeleton template application succeeds for new satellite init
- [ ] Hook/skill/agent registration works without manual intervention
- [ ] Migration runbooks execute successfully (no "it works on my machine")
- [ ] Compatibility matrix reflects actual tested combinations
- [ ] Breaking changes have documented upgrade paths
- [ ] No regressions in existing satellite functionality
- [ ] Roster updates propagate to all satellites via `cem sync`
- [ ] Error messages trace to specific ecosystem component (not vague "sync failed")

---

## Anti-Patterns to Avoid

- **Feature Creep**: This team builds infrastructure, not features. If it's a satellite-specific capability, route to 10x-dev-pack.
- **Skipping Validation**: "It worked in skeleton" ≠ success. Must test against satellite matrix.
- **Undocumented Breaking Changes**: If it breaks `cem sync`, it needs a migration runbook. No exceptions.
- **Vague Error Messages**: "Sync failed" is not actionable. Trace to specific component.
- **Premature Optimization**: CEM doesn't need to scale to 10,000 satellites. Optimize for clarity first.
- **Schema Drift**: Hook/skill schemas must match roster documentation. Single source of truth.

---

## Integration with Other Teams

### Forge Teams

- **Prompt Architect**: Receives TEAM-SPEC to create actual agent prompts
- **Workflow Engineer**: Receives agent specs to design command workflows
- **Eval Specialist**: Receives Compatibility Report format to design validation tests

### Domain Teams

- **team-development** (owns agent/team/command content in roster): Collaborates on schema changes
- **10x-dev-pack**: Escalates satellite-specific issues here if root cause is ecosystem
- **doc-team-pack**: Uses Migration Runbooks as input for user-facing upgrade guides

---

## Related Skills

- [team-development](../team-development/skill.md) - Team/agent/command development patterns
- [standards](../standards/skill.md) - Repository structure, code conventions
- [10x-workflow](../10x-workflow/skill.md) - General workflow principles (different artifacts)

---

## Versioning Strategy

Ecosystem components follow semantic versioning:

- **CEM**: Major = breaking CLI changes, Minor = new features, Patch = bug fixes
- **Skeleton**: Major = breaking schema changes, Minor = new hooks/patterns, Patch = fixes
- **Roster**: Version = timestamp (acts as content registry, not versioned software)

**Compatibility Requirement**: CEM version N must work with skeleton version N-1 (one major version backward compatibility).
