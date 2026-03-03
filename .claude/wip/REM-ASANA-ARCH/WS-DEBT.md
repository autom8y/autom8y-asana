# WS-DEBT: Query v1 Sunset Consumer Audit

**Objective**: Audit the v1 query API endpoint for active consumers before the
2026-06-01 sunset date, and either remove the endpoint (if no traffic) or
create a migration plan (if consumers exist).

**Rite**: debt-triage
**Complexity**: PATCH
**Referrals**: XR-ARCH-002 (v1 sunset consumer audit)
**Related Debt**: D-002 (v1 query router full removal, calendar-gated 2026-06-01)
**Preconditions**: None (independent)
**Estimated Effort**: 1-2 days

---

## Problem

The v1 query endpoint has a 2026-06-01 sunset date (~14 weeks from analysis date).
No consumer inventory exists in code artifacts. If v1 has active consumers who
have not migrated to v2, the sunset requires either an extension or forced migration.

D-002 (v1 query router full removal) is calendar-gated to 2026-06-01.

**Evidence**: ARCHITECTURE-REPORT.md Section 8, XR-ARCH-002;
ARCHITECTURE-ASSESSMENT.md Gap 7 (low confidence)

---

## Artifact References

- Query router: `src/autom8_asana/api/routes/query.py` (v1/v2 merged per MEMORY.md)
- Gap analysis: `ARCHITECTURE-ASSESSMENT.md` Section 5.2, Gap 7
- Debt item: `docs/debt/LEDGER-cleanup-modernization.md` (D-002)

---

## Investigation Steps

### Step 1: Code Audit

1. Read `src/autom8_asana/api/routes/query.py` to identify v1-specific routes
2. Search for any v1 query URL patterns in the codebase:
   ```
   grep -rn "v1/query\|/v1/query" src/ tests/ docs/
   ```
3. Check for v1 consumer documentation or migration guides

### Step 2: Traffic Audit (Requires Operational Access)

1. Check API access logs (CloudWatch) for v1 query endpoint traffic
2. Identify unique consumers (by API key, IP, user-agent)
3. Determine traffic volume and patterns

### Step 3: Decision

**If zero v1 traffic**:
- Remove v1 query endpoint routes
- Close D-002 ahead of schedule
- Update MEMORY.md

**If v1 has active traffic**:
- Create consumer inventory (who, what, how much)
- Notify consumers of sunset date
- Provide v2 migration guide
- Set 4-week check-in before 2026-06-01
- File as sprint-ready debt item with deadline

### Step 4: Document

- Update `docs/debt/LEDGER-cleanup-modernization.md` D-002 with findings
- If consumers found: create migration tracking doc

---

## Do NOT

- Remove v1 endpoint without confirming zero traffic
- Extend the sunset date without documenting justification
- Change v2 query behavior as part of this workstream

---

## Green-to-Green Gates

- If endpoint removed: all tests pass, no v1-specific tests fail
- If migration plan created: document has consumer list, timeline, and owner

---

## Definition of Done

- [ ] v1 consumer inventory complete (zero consumers or named list)
- [ ] Decision documented: remove now OR migration plan with timeline
- [ ] D-002 debt item updated with current status
- [ ] MEMORY.md updated: "WS-DEBT: v1 audit complete, [outcome]"
