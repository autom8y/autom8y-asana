# Initiative Index: SSoT Convergence & Reliability Hardening

**Updated**: 2026-02-17 (WS2 complete)
**Branch**: main (post-merge)
**Merge commit**: ca1f7fa

## Workstream Status
| WS | Status | Checkpoint | Domain |
|----|--------|-----------|--------|
| WS1 | COMPLETE | (archived at docs/.archive/2026-02-ws1/) | Entity registry, dataframes |
| WS2 | COMPLETE | .claude/wip/WS2-CHECKPOINT.md (commit 2977717) | Cache subsystem |
| WS3 | NOT STARTED | .claude/wip/WS3-CHECKPOINT.md | Traversal, cascade |

## Cross-WS Dependencies
- WS3 depends on WS1 (EntityDescriptor fields) -- SATISFIED (merged)
- WS3 depends on WS2 (CascadeViewPlugin uses cache-backed UnifiedTaskStore) -- sequence WS2 first
- WS2 and WS3 touch separate subsystems (cache/ vs dataframes/resolver/ + views/)

## Execution Plan
| Phase | Scope | Agent Sequence |
|-------|-------|----------------|
| WS2-Arch | Cache reliability TDD | Architect |
| WS2-S1 | Invalidation + staleness | PE |
| WS2-S2 | Warm-up + unified store + QA | PE then QA |
| WS3-Arch | Traversal consolidation TDD | Architect |
| WS3-S1 | B/C consolidation (CascadeViewPlugin primary) | PE |
| WS3-S2 | Cascade promotion + QA | PE then QA |

## Global Decisions
- Context: checkpoint docs, not resumption; pointers not content
- Branch: all work on main post-merge (single branch constraint)
- Session boundaries: 1 per sprint, fresh session at workstream switches
- Pre-existing test failures: test_adversarial_pacing, test_paced_fetch, test_cache_errors_logged_as_warnings
- Test baseline: 10,582 passed at WS2 complete (was 10,575 at WS1 merge)

## Key Reference Documents
- Spike research: docs/spikes/SPIKE-deferred-todo-triage.md
- WS1 ARCH doc: docs/design/ARCH-descriptor-driven-auto-wiring.md
- S4 Amendment: docs/design/TDD-S4-AMENDMENT.md (ADR-S4-001)
- WS2 TDD: docs/design/TDD-WS2-CACHE-RELIABILITY.md (ADR-WS2-001)
- Deferred items: .claude/wip/TODO.md
