# Archived Skill Files

This directory contains skill files that were split or reorganized during the Skills migration.

## Files in This Archive

### tech-stack.md (480 lines)
**Archived**: December 11, 2024 (Session 5.75)
**Reason**: Split into 5 domain-specific files for progressive disclosure
**Replaced by**:
- `tech-stack-core.md` - Universal technology policies
- `tech-stack-python.md` - Python ecosystem
- `tech-stack-go.md` - Go ecosystem
- `tech-stack-infrastructure.md` - Databases, Docker, cloud
- `tech-stack-api.md` - REST API standards

**Token Savings**: 50-77% reduction depending on task type

### glossary.md (410 lines)
**Archived**: December 11, 2024 (Session 5.75)
**Reason**: Split into 4 domain-specific files for progressive disclosure
**Replaced by**:
- `glossary-index.md` - Navigation to all terms
- `glossary-agents.md` - Agent roles and artifacts
- `glossary-process.md` - Workflow phases and concepts
- `glossary-quality.md` - Quality concepts and anti-patterns

**Token Savings**: 60-77% reduction depending on domain

## Why Split?

Large monolithic files meant loading 400-500 lines of context even when only needing 100-200 lines of domain-specific guidance. Splitting enables:
- Context-aware activation based on task type
- 50-77% token reduction for focused work
- Clearer semantic organization
- Independent domain evolution

## Rollback

Original files preserved for reference. However, the split versions are now canonical.
