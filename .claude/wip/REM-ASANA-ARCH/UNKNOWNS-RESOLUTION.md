# Unknowns Quick Resolution Guide

10 unknowns from the DEEP-DIVE architecture analysis. Most resolve in under
5 minutes with a single command or file read.

Source: `ARCHITECTURE-REPORT.md` Section 9

---

## U-001: Whether lifecycle handles all automation scenarios

**Impact**: HIGH
**Resolution time**: 30-60 min (feature comparison)
**Blocks**: Long-term planning (not any immediate workstream)

### Resolution Steps

1. Read both files and diff their capabilities:
   ```
   grep -n "def.*async" src/autom8_asana/lifecycle/creation.py
   grep -n "def.*async" src/autom8_asana/automation/pipeline.py
   ```

2. Search for automation-only features:
   ```
   grep -n "_create_onboarding_comment_async\|_validate_post_transition\|FR-COMMENT" \
     src/autom8_asana/automation/pipeline.py
   ```

3. Check if lifecycle has equivalents:
   ```
   grep -n "onboarding_comment\|post_transition\|FR-COMMENT" \
     src/autom8_asana/lifecycle/
   ```

4. **Decision**: If automation has unique capabilities not in lifecycle, the
   dual-path architecture is permanent. If all capabilities exist in lifecycle,
   `automation/pipeline.py` is a deprecation candidate.

5. Document outcome in MEMORY.md.

---

## U-002: Classification rule change frequency

**Impact**: HIGH
**Resolution time**: 5 min
**Blocks**: WS-CLASS (R-004)

### Resolution Command

```bash
cd /Users/tomtenuta/Code/autom8y-asana
git log --oneline --all -- src/autom8_asana/models/business/activity.py | head -20
```

Then check specific changes to classifier data:
```bash
git log -p -- src/autom8_asana/models/business/activity.py \
  | grep -c "OFFER_SECTIONS\|UNIT_SECTIONS\|frozenset"
```

**Decision rule**:
- 3+ changes in 6 months -> EXECUTE WS-CLASS
- 0-2 changes in 6 months -> SKIP WS-CLASS, document as "stable"

---

## U-003: conversation_audit.py bootstrap guard status

**Impact**: MEDIUM
**Resolution time**: 2 min
**Blocks**: WS-QW (R-001)

### Resolution Command

```bash
grep -n "import autom8_asana.models.business\|_ensure_bootstrap\|bootstrap" \
  /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/conversation_audit.py
```

**If found**: R-001 is a verification only (mark done).
**If not found**: R-001 requires adding the import guard.

---

## U-004: Query v1 consumer inventory

**Impact**: MEDIUM
**Resolution time**: 15-30 min (code audit) + operational data needed
**Blocks**: WS-DEBT

### Resolution Steps

1. Code-level check:
   ```bash
   grep -rn "v1/query\|/v1/query" \
     /Users/tomtenuta/Code/autom8y-asana/src/ \
     /Users/tomtenuta/Code/autom8y-asana/tests/ \
     /Users/tomtenuta/Code/autom8y-asana/docs/
   ```

2. Check the query router for v1-specific routes:
   ```bash
   grep -n "v1\|deprecated\|sunset" \
     /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py
   ```

3. For traffic data: requires CloudWatch API access log analysis (operational,
   not code-resolvable).

---

## U-005: Deferred import cold-start latency

**Impact**: MEDIUM
**Resolution time**: Not resolvable from code -- requires runtime profiling
**Blocks**: Nothing immediate

### Resolution Approach

This requires Lambda cold-start performance profiling. Cannot resolve from
code artifacts. Two options:

1. Check CloudWatch metrics for `cache_warmer` handler initialization time
2. Local profiling:
   ```bash
   cd /Users/tomtenuta/Code/autom8y-asana
   python -X importtime -c "import autom8_asana" 2>&1 | head -50
   ```

**Action**: File as observability task if cold-start latency is a concern.
Otherwise, accept as low-priority unknown.

---

## U-006: system_context.py design intent

**Impact**: MEDIUM
**Resolution time**: 10 min
**Blocks**: WS-SYSCTX (provides confidence in approach)

### Resolution Steps

1. Check the original QW-5 reference:
   ```bash
   find /Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ -name "ARCH-REVIEW-1*" \
     | head -5
   ```

2. Read Section 3.1 of the arch review that spawned QW-5.

3. Check git history:
   ```bash
   git log --oneline --follow \
     /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/system_context.py \
     | head -10
   ```

**Expected outcome**: Confirms it was a pragmatic test utility (not a designed
architectural element), validating R-005 registration pattern approach.

---

## U-007: cloudwatch.py bootstrap status

**Impact**: LOW
**Resolution time**: 2 min
**Blocks**: WS-QW (R-007)

### Resolution Command

```bash
head -50 /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cloudwatch.py
```

Then check for entity detection usage:
```bash
grep -n "models.business\|detect_entity\|entity_type\|bootstrap" \
  /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cloudwatch.py
```

**If no entity detection**: Document as "no bootstrap required" in entry-point audit.
**If entity detection used**: Add bootstrap guard per R-007.

---

## U-008: Pre-existing test failures status

**Impact**: LOW
**Resolution time**: 5 min
**Blocks**: WS-HYGIENE (XR-ARCH-006)

### Resolution Command

```bash
cd /Users/tomtenuta/Code/autom8y-asana
pytest tests/ -k "adversarial_pacing or paced_fetch" --tb=short 2>&1 | tail -20
```

**If passing**: Update MEMORY.md ("pre-existing test failures resolved").
**If failing**: Triage as behavioral gap vs. aspirational test in WS-HYGIENE.

---

## U-009: Internal/admin router endpoint inventory

**Impact**: LOW
**Resolution time**: 5 min
**Blocks**: Nothing

### Resolution Commands

```bash
grep -n "def \|@router" \
  /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/internal.py
```

```bash
grep -n "def \|@router" \
  /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/admin.py
```

Document findings in topology notes. No action required unless undocumented
operational endpoints are found.

---

## U-010: Polling CLI deployment status

**Impact**: LOW
**Resolution time**: 5 min (code check) + infra verification
**Blocks**: Nothing

### Resolution Steps

1. Check pyproject.toml:
   ```bash
   grep -A3 "scheduler\|polling\|apscheduler" \
     /Users/tomtenuta/Code/autom8y-asana/pyproject.toml
   ```

2. Check for production deployment references:
   ```bash
   grep -rn "polling/cli\|automation.polling" \
     /Users/tomtenuta/Code/autom8y-asana/.github/ \
     /Users/tomtenuta/Code/autom8y-asana/Dockerfile \
     /Users/tomtenuta/Code/autom8y-asana/docker-compose.yml
   ```

**Expected outcome**: Confirms dev-only tool (pyproject.toml says "development mode").
If no deployment references found, document as "dev-only, no production entry point."

---

## Resolution Priority Order

| Priority | Unknown | Time | Reason |
|----------|---------|------|--------|
| 1 | U-003 | 2 min | Blocks WS-QW R-001 |
| 2 | U-007 | 2 min | Blocks WS-QW R-007 |
| 3 | U-002 | 5 min | Blocks WS-CLASS |
| 4 | U-008 | 5 min | Blocks WS-HYGIENE XR-006 |
| 5 | U-006 | 10 min | Informs WS-SYSCTX approach |
| 6 | U-009 | 5 min | Documentation completeness |
| 7 | U-010 | 5 min | Documentation completeness |
| 8 | U-001 | 30-60 min | Long-term planning |
| 9 | U-004 | 15-30 min | Needs operational data |
| 10 | U-005 | N/A | Needs runtime profiling |

**Total time for top 7**: ~35 minutes. Do these in a single session before
starting any workstream.
