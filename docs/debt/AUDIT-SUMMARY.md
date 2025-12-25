# Documentation Debt Audit Summary

**Date**: 2025-12-24
**Session**: session-20251224-232654-1a1ac669
**Auditor**: debt-collector agent
**Scope**: Full documentation surface (docs/, .claude/, README.md)

---

## Quick Stats

- **Total Debt Items**: 47
- **Critical Items**: 8 (17%)
- **Estimated Remediation**: 28-42 hours (3.5-5 days)
- **Files Audited**: 464 markdown files

## Top 5 Critical Issues

1. **INDEX.md status metadata divergence** - 13+ PRDs show wrong status, developers can't trust documentation index
2. **15 PROMPT-* files mislocated** - Initiative files in /requirements/ instead of /initiatives/, confuses taxonomy
3. **Broken skill references** - PROJECT_CONTEXT.md references deleted autom8-asana skill
4. **40+ uncommitted doc changes** - High risk of work loss, unclear what's been reviewed
5. **Superseded docs not marked** - PRD-PROCESS-PIPELINE, PRD-0021, PRD-0022 describe rejected features but marked "Active"

## By Category

| Category | Count | % |
|----------|-------|---|
| Outdated Content | 15 | 32% |
| Structural Issues | 10 | 21% |
| Missing Documentation | 9 | 19% |
| Quality Issues | 7 | 15% |
| Stale Artifacts | 4 | 9% |
| Redundant/Duplicate | 2 | 4% |

## Recommended Next Steps

### Immediate (Today)
1. Commit uncommitted changes (DEBT-040)
2. Fix INDEX.md status metadata (DEBT-001)
3. Fix broken skill reference (DEBT-026)

### This Week
4. Move PROMPT-* files to /initiatives/ (DEBT-016)
5. Mark superseded docs (DEBT-008, 005, 006, 007)
6. Archive completed initiatives (DEBT-021)

### This Sprint
7. Create directory READMEs (DEBT-017, 022, 025)
8. Update stale PRDs (DEBT-002, 003, 004)
9. Create operational runbooks (DEBT-027)

## Full Details

See [LEDGER-doc-debt-inventory.md](LEDGER-doc-debt-inventory.md) for complete inventory with:
- 47 detailed debt items
- Evidence and suggested fixes
- Priority ordering
- Effort estimates
- Dependency analysis
- Root cause analysis

## Handoff

**Ready for**: risk-assessor agent
**Next step**: Score items for probability × impact, validate severity, recommend sprint packaging

**Files**:
- `/docs/debt/LEDGER-doc-debt-inventory.md` - Complete inventory
- `/docs/debt/AUDIT-SUMMARY.md` - This summary
