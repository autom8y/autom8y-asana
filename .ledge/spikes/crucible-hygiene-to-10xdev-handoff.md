---
type: cross-rite-handoff
initiative: project-crucible
from_rite: hygiene
to_rite: 10x-dev
handoff_scope: sprint-3-and-sprint-4
generated: 2026-04-15
generator: audit-lead
verdict: READY-FOR-TRANSFER
source_session: session-20260415-032649-5912eaec
---

# Project Crucible — Hygiene → 10x-Dev Handoff

> This artifact is self-contained. A fresh 10x-dev session can resume sprint-3 without re-reading prior conversation history. Load this file + the two sprint audit reports referenced below.

## 1. Hygiene Rite Deliverables (What's Done)

### Sprint-1: Fixture Consolidation (6 commits)

| Commit | Short SHA | Description |
|--------|-----------|-------------|
| RF-001 | `f0231b98` | Remove unused MockClientBuilder (80 LOC dead code) |
| RF-002 | `778ba707` | Fix S9 double-reset in api/conftest.py |
| RF-003 | `03e54aa7` | Extend shared MockCacheProvider with get_metrics() |
| RF-004 | `28b1375d` | Create CacheDomainMockProvider in cache/conftest.py |
| RF-005 | `f22b0066` | Consolidate persistence/ MockCacheProvider variants |
| RF-006 | `5b4565d3` | Add `client_factory` fixture to clients/conftest.py |

**Outcome**:
- MockCacheProvider proliferation: **9:1 → 1.5:1**
- `client_factory` fixture available for cross-client parametrize (sprint-3 foundation)
- S9 defensive pattern landed (double-reset eliminated)

### Sprint-2: Framework-Waste Removal (13 commits)

Range: `4b139a88..8a0bab6a` (CRU-S2-001 .. CRU-S2-013)

| Commit | Short SHA | File(s) | Removed |
|--------|-----------|---------|---------|
| CRU-S2-001 | `4b139a88` | `test_models.py` | 23 |
| CRU-S2-002 | `a17c23ec` | `test_common_models.py` | 5 |
| CRU-S2-003 | `e81eeca3` | `business/test_base.py` | 6 |
| CRU-S2-004 | `d2fb8fcd` | `business/test_activity.py` | 5 |
| CRU-S2-005 | `5d8bfc86` | `business/test_unit.py`, `test_offer.py` | 2 |
| CRU-S2-006 | `084f4db6` | `business/test_resolution.py` | 2 |
| CRU-S2-007 | `4d5fdb01` | `business/test_business.py` | 2 |
| CRU-S2-008 | `a38cf250` | `business/test_seeder.py` | 2 |
| CRU-S2-009 | `1194b1a1` | `business/test_process.py` | 3 |
| CRU-S2-010 | `ac2e5048` | `business/test_contact.py`, `test_location.py`, `test_hours.py` | 3 |
| CRU-S2-011 | `1e8708c5` | `business/test_asset_edit.py` | 1 |
| CRU-S2-012 | `ffcbe7a1` | `business/test_patterns.py` | 2 |
| CRU-S2-013 | `8a0bab6a` | `clients/test_client.py`, `clients/data/test_models.py` | 4 |

**Outcome**: 60 framework-testing waste functions removed (vs. 112 audit-estimate; 52-function shortfall justified per-file in sprint-2 audit report).

### Current Codebase State at HEAD (`8a0bab6a`)

| Metric | Value |
|--------|-------|
| Branch | `main` |
| Total collectable tests (non-integration) | ~13,080 |
| Tests passing (verified) | 12,532 passed, 47 xfailed, 6 xpassed, 2 skipped |
| Coverage | ≥ 87.61% (maintained — zero src/ changes in sprint-1+2) |
| xdist parallel | ENABLED (CHANGE-003) |
| CI shard matrix | 4 shards ACTIVE (CHANGE-004) |
| Async marker cleanup | COMPLETE (2,588 redundant markers removed, CHANGE-007) |

---

## 2. Category B Catalog (Sprint-3 Primary Consumption)

Category B = "Behavior-Boundary Inversion" tests that assert on mock-call state rather than observable behavior. Sprint-3's parametrize campaign is the intended vehicle to collapse these into parametrize tables.

### High-Priority Category B (recommended sprint-3 targets)

| File | Est. Functions | Pattern | Notes |
|------|----------------|---------|-------|
| `tests/unit/clients/test_tier1_clients.py` | **~40** | `mock_http.{verb}.assert_called_once_with(...)` + fused isinstance checks | Compound with parametrize — removes ~14 residual Category A isinstance assertions as side-effect |
| `tests/unit/clients/test_tier2_clients.py` | **~55** | Same inversion pattern | Same fusion benefit |
| `tests/unit/clients/test_tasks_client.py` | **~11** | Same pattern | Small but pure signal |
| `tests/unit/models/test_models.py` (TasksClient filter inversions) | **~8** | Filter-wiring assertions | Overlaps Category B territory in the TasksClient section of test_models.py |

**Combined sprint-3 primary scope**: ~114 functions in this high-priority band.

### Broader Client Category B

Per the sprint-2 audit (Category B section), **~370 functions total (~42% of 882)** across `tests/unit/clients/` show boundary-inversion patterns. The 114 above are the highest-confidence signals; the remaining ~256 may need per-file judgment.

### Deferred (NOT sprint-3 scope)

| Area | Reason |
|------|--------|
| `tests/unit/clients/data/` subdirectory (20 files) | **TENSION-001 risk** — requires architect-enforcer clearance before touching |
| `tests/unit/clients/test_batch.py` | Mostly Category C (batch orchestration logic is application behavior) |
| `tests/unit/events/*` | Out of Domain 2 scope; preserved MockCacheProvider per SCAR sensitivity |

---

## 3. Fixture State (Sprint-3 Parametrize Foundation)

### Available Fixtures

| Fixture | Location | Purpose | Key Direction |
|---------|----------|---------|---------------|
| `client_factory` | `tests/unit/clients/conftest.py` | Cross-client parametrize factory (sprint-3 primary tool) | N/A |
| `MockCacheProvider` (shared) | `tests/unit/clients/conftest.py` | Shared client-test cache mock | `key:type` |
| `CacheDomainMockProvider` | `tests/unit/cache/conftest.py` | Cache-domain-specific mock | `type:key` |
| `MockCacheProviderForInvalidation` | `tests/unit/persistence/conftest.py` | Persistence-specific invalidation mock | (consolidated in RF-005) |

### Fixture Key-Direction Gotcha

**CRITICAL for sprint-3**: Two MockCacheProvider variants use **opposite key directions**:

- `clients/conftest.py` uses `key:type` ordering
- `cache/conftest.py` uses `type:key` ordering

When writing parametrize tests that cross these boundaries, do NOT assume key format symmetry. The divergence is **intentional** (each reflects the real cache key convention of its domain). Verify with the shared fixture module before building cross-domain parametrize tables.

### Local Fixture Count

Still approximately **591 local fixtures** across test tree. RF-007 ("local fixture promotion 591 → 350") was **deferred** — the original methodology estimate was flawed (see Open Items §7). AST-based re-measurement required before sprint-3 can safely promote local fixtures.

### `test_events.py` MockCacheProvider — PRESERVED

This file's MockCacheProvider is intentionally NOT consolidated. Reason: scar-sensitive — events test coverage encodes subtle ordering invariants that the shared provider does not preserve. **Do not touch this file** in sprint-3 unless the scope is explicitly expanded via architect-enforcer consultation.

---

## 4. Sprint-3 Mission (from the Shape)

**Primary Domain**: Parametrize Campaign (Domain 1) + Boundary Refactoring (Domain 2 Category B) — **single-pass combined execution**.

### Scope

| Package | Function Count | Target Reduction |
|---------|----------------|------------------|
| `tests/unit/clients/` (excl. data/) | 880 functions | → **~200–250** functions |
| `tests/unit/models/` (post-sprint-2) | ~1,350 functions | TBD per sprint-3 micro-audit |

### Tooling

- Use `client_factory` fixture for cross-client parametrize
- Use `pytest.mark.parametrize` tables consolidating families of copy-paste tests
- Preserve Category C tests (legitimate application behavior) unchanged

### Required Per-Commit Discipline

1. **Audit each conversion against scar-tissue map** (`.know/scar-tissue.md`, 33 scars) BEFORE merging
2. **Run full test suite after every commit** (not just subtree)
3. **Coverage floor 80%** verified at phase boundaries
4. **Commit naming**: `refactor(tests): CRU-S3-NNN — <desc>`
5. **Independent revertibility**: each commit must revert cleanly without inter-commit coupling

### Estimated Sprint-3 Deliverables

- 20–40 commits in CRU-S3-NNN range
- ~630 functions collapsed into parametrize tables (rough projection — confirm with micro-audit at sprint-3 kickoff)
- `tests/unit/clients/` reduced by 70%+ in raw function count without coverage loss
- Residual Category A client functions (~14) cleared as side-effect

---

## 5. Sprint-4 Mission (from the Shape)

**Primary Domain**: Extended Parametrize — other packages.

### Scope

| Package | Status |
|---------|--------|
| `tests/unit/automation/` | Pattern prevalence UNKNOWN — per-package audit needed at sprint-4 kickoff |
| `tests/unit/persistence/` | Pattern prevalence UNKNOWN |
| `tests/unit/dataframes/` | Pattern prevalence UNKNOWN |
| `tests/unit/cache/` | Pattern prevalence UNKNOWN |
| `tests/unit/core/` | Pattern prevalence UNKNOWN |

### Required Pre-Work

Sprint-4 cannot scope itself without a **per-package audit** (code-smeller or lightweight manual scan) at kickoff. Do NOT assume sprint-3's parametrize patterns apply uniformly — the client package has unusually high boundary-inversion density (42%); other packages may be dominated by Category C.

### Target

Collapse remaining copy-paste families; no hard function-count target until audit lands.

---

## 6. Sacred Constraints (NEVER Violate)

These constraints apply to **both sprint-3 and sprint-4**. Violation = immediate rollback.

1. **33 scar-tissue tests PRESERVED** — full list in `.know/scar-tissue.md` (SCAR-001 through SCAR-030 + SCAR-S3-LOOP + 2 new scars from commits `944a0e7` and `e89875f`). Any test file referenced in a SCAR entry must be audited before modification.

2. **Coverage floor: 80%** — measured at phase boundaries, not per-commit. Current baseline: 87.61%.

3. **No production source changes** — all sprint-3/4 work is `tests/`-only. If a conversion *seems* to require src changes, STOP and escalate to architect-enforcer.

4. **Independent revertibility per commit** — every commit must stand alone.

5. **`test_events.py` MockCacheProvider PRESERVED** — do not consolidate, do not refactor.

6. **TENSION-001 `data/` subdirectory REQUIRES CLEARANCE** — `tests/unit/clients/data/*` is off-limits until architect-enforcer issues a TENSION-001-cleared plan. Sprint-3 scope explicitly excludes this subtree.

7. **SCAR-026 territory** — MagicMock-based tests in client files carry `spec=` enforcement sensitivity. ADD `spec=` arguments where absent; DO NOT remove MagicMock-based tests without scar-tissue review.

8. **SCAR-025 territory** — `PRIMARY_PROJECT_GID` and `NAME_CONVENTION` class-attribute tests encode GID contract invariants. Preserve even when they look like framework-waste.

9. **SCAR-001 territory** — `test_registry.py` and `test_registry_consolidation.py` encode entity-collision contracts. Do not refactor without SCAR-001 review.

---

## 7. Open Items Carried Forward

| Item | Status | Recommended Disposition |
|------|--------|-------------------------|
| **RF-007 local fixture promotion** (591 → 350 target) | DEFERRED | Requires AST-based methodology redesign. Original heuristic count was unreliable. Park until sprint-5+ or debt-rite followup. |
| **SCAR-026 spec= enforcement** | PARALLEL TRACK | ADD not remove. Can run concurrent with sprint-3 but do NOT merge into CRU-S3-NNN commits — use separate `chore(tests): SCAR-026 — ...` commits. |
| **Category B refactoring (~417 functions)** | SPRINT-3 PRIMARY SCOPE | See §2 and §4. |
| **47 xfail-masked OpenAPI violations (S10)** | SEPARATE RITE | Route to architecture rite via a new HANDOFF artifact. Do NOT attempt in 10x-dev. |
| **`test_seeder.py` ContactData Category A residue** | BACKLOG | Fold into first sprint-3 conversion that touches `test_seeder.py`. Small (~2 functions). |
| **`test_detection.py` frozen-dataclass tests** | REQUIRES ADR | If sprint-3 wants to include, escalate to architect-enforcer for immutability-ADR reference. |

---

## 8. Verification Protocol for 10x-Dev

Sprint-3 and sprint-4 commits MUST satisfy this protocol before being considered complete.

### Per-Commit

```bash
# 1. Full non-integration test suite MUST pass
uv run pytest tests/ -x --timeout=120 -q -m 'not integration and not benchmark'

# 2. Ruff must pass
uv run ruff check src/ tests/

# 3. Commit message format
refactor(tests): CRU-S3-NNN — <description>
# or
refactor(tests): CRU-S4-NNN — <description>
```

### Per-Phase (end of logical phase within a sprint)

```bash
# 1. Coverage check
uv run pytest tests/ --cov=src --cov-report=term --timeout=120 \
  -m 'not integration and not benchmark' 2>&1 | tail -20
# Assert: total coverage >= 80%

# 2. Scar-tissue regression sweep
uv run pytest tests/unit/core/test_entity_registry.py \
  tests/unit/reconciliation/test_section_registry.py \
  tests/unit/dataframes/test_cascade_ordering_assertion.py \
  tests/unit/dataframes/test_warmup_ordering_guard.py \
  tests/unit/models/business/matching/test_normalizers.py \
  -q --timeout=60
# Assert: 238+ passing (baseline established 2026-04-15)
```

### Per-Sprint (before handoff to next rite)

1. Full test suite green
2. Coverage floor met
3. Sprint audit report in `.sos/wip/crucible/sprint-3-audit-report.md` (or sprint-4)
4. Commit atomicity verified by git log inspection
5. Update this handoff artifact or produce a successor if continuing

---

## 9. Session Transition

### Current Session (at time of handoff)

- **Session ID**: `session-20260415-032649-5912eaec`
- **Rite**: `hygiene` (ACTIVE)
- **Status**: Sprint-2 complete, awaiting cross-rite transition

### Next Steps for 10x-Dev

```bash
# 1. Verify rite has been switched
ari rite current
# Expected output: 10x-dev (ACTIVE)

# 2a. If continuing from parked session:
/sos resume

# 2b. If starting fresh sprint-3 session:
/go
# or
/sos start crucible-sprint-3

# 3. Load context for sprint-3
# Read in this order:
#   a. .sos/wip/frames/crucible.shape.md          (frame + shape — mission scope)
#   b. .ledge/spikes/crucible-hygiene-to-10xdev-handoff.md  (this file)
#   c. .sos/wip/crucible/sprint-2-audit-report.md (what sprint-2 did)
#   d. .sos/wip/crucible/sprint-1-audit-report.md (fixture foundation)
#   e. .know/scar-tissue.md                       (33 scars — sacred constraints)
```

### Context Budget Estimate

- Handoff artifact (this file): ~6k tokens
- Sprint-2 audit report: ~4k tokens
- Sprint-1 audit report: ~3k tokens
- Shape + frame: ~5k tokens
- Scar-tissue: ~8k tokens
- **Total bootstrap**: ~26k tokens — comfortable for a fresh 10x-dev agent session

---

## 10. Handoff Acceptance Criteria

The 10x-dev rite MAY accept this handoff when:

- [x] All sprint-2 CRU-S2-NNN commits verified atomic and reversible
- [x] Sprint-2 audit verdict issued (APPROVED WITH NOTES)
- [x] Category B catalog enumerated for sprint-3 consumption
- [x] Fixture state documented with key-direction gotchas
- [x] Sacred constraints enumerated and non-negotiable
- [x] Open items triaged (this sprint, later sprint, different rite)
- [x] Verification protocol spec'd for sprint-3/4 commits
- [x] Session transition commands documented
- [x] Context bootstrap list provided

**Handoff verdict**: **READY-FOR-TRANSFER**.

---

## Appendix A: Key File Paths (Absolute)

| Purpose | Path |
|---------|------|
| This handoff | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/crucible-hygiene-to-10xdev-handoff.md` |
| Sprint-2 audit report | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/crucible/sprint-2-audit-report.md` |
| Sprint-2 behavior audit (plan) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/crucible/sprint-2-behavior-audit-report.md` |
| Sprint-2 execution log | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/crucible/sprint-2-framework-removal-log.md` |
| Sprint-1 audit report | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/crucible/sprint-1-audit-report.md` |
| Sprint-1 fixture log | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/crucible/sprint-1-fixture-consolidation-log.md` |
| Sprint-1 refactoring plan | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/crucible/sprint-1-refactoring-plan.md` |
| Scar-tissue catalog | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/scar-tissue.md` |
| Shared client fixtures | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/clients/conftest.py` |
| Cache domain fixtures | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/cache/conftest.py` |
| Persistence fixtures | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/persistence/conftest.py` |

## Appendix B: Commit SHA Quick Reference

```
Sprint-1 (RF-00N fixture consolidation):
  f0231b98  RF-001  remove MockClientBuilder
  778ba707  RF-002  fix S9 double-reset
  03e54aa7  RF-003  extend MockCacheProvider.get_metrics
  28b1375d  RF-004  CacheDomainMockProvider in cache/conftest
  f22b0066  RF-005  consolidate persistence/ variants
  5b4565d3  RF-006  client_factory fixture

Sprint-2 (CRU-S2-NNN framework-waste removal):
  4b139a88  CRU-S2-001  test_models.py                         (-23)
  a17c23ec  CRU-S2-002  test_common_models.py                  (-5)
  e81eeca3  CRU-S2-003  business/test_base.py                  (-6)
  d2fb8fcd  CRU-S2-004  business/test_activity.py              (-5)
  5d8bfc86  CRU-S2-005  business/test_unit.py + test_offer.py  (-2)
  084f4db6  CRU-S2-006  business/test_resolution.py            (-2)
  4d5fdb01  CRU-S2-007  business/test_business.py              (-2)
  a38cf250  CRU-S2-008  business/test_seeder.py                (-2)
  1194b1a1  CRU-S2-009  business/test_process.py               (-3)
  ac2e5048  CRU-S2-010  business/test_contact/location/hours   (-3)
  1e8708c5  CRU-S2-011  business/test_asset_edit.py            (-1)
  ffcbe7a1  CRU-S2-012  business/test_patterns.py              (-2)
  8a0bab6a  CRU-S2-013  clients/test_client + data/test_models (-4)

HEAD: 8a0bab6a  (baseline for sprint-3)
```

— audit-lead, 2026-04-15, session `session-20260415-032649-5912eaec`
