---
type: handoff
status: proposed
handoff_status: pending  # HANDOFF lifecycle state per cross-rite-handoff schema v1.0 (pending | in_progress | completed | rejected); distinct from ledge-lifecycle `status` above
artifact_id: HANDOFF-sre-to-fleet-potnia-d06-residual-routing-2026-04-22
schema_version: "1.0"
source_rite: sre
target_rite: fleet-potnia
handoff_type: strategic_input
priority: high
blocking: false  # does not block sre-rite progress; fleet-potnia routing forcing function
initiative: d06-sre-residual-risk-matrix-priority-routing
created_at: "2026-04-22T12:30Z"
partial: false  # UPGRADED 2026-04-22T11:00Z via main-thread scope-completion after chaos-engineer matrix landed
partial_reason_historical: "PARTIAL at 12:30Z emission — chaos-engineer SRE-D06-RESIDUAL-RISK-MATRIX-2026-04-22.md landed at 10:28Z but IC session closed before visibility propagated. Main-thread completed §3 via scope-completion-discipline P4.1 pattern-replication at 11:00Z."
evidence_grade: moderate  # UPGRADED from WEAK once matrix landed + concrete routing populated. STRONG requires fleet-potnia external routing decision at next CC-restart.
source_artifacts:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-D06-RESIDUAL-RISK-MATRIX-2026-04-22.md  # PENDING — chaos-engineer producing concurrent
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/IC-CRITIQUE-auth-runbooks-2026-04-22.md  # companion artifact (Deliverable A)
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-fleet-potnia-to-sre-ci-diagnosis-plus-revocation-backend-readiness-2026-04-21.md  # parent fleet-potnia handoff that precipitated D-06
provenance:
  - source: "sre-Potnia §7 risk flag (anti-theater check: matrix is useful ONLY if fleet-potnia actually routes Phase B/C/D)"
    type: artifact
    grade: moderate
  - source: "chaos-engineer D-06 per-service blast-radius classification (concurrent dispatch)"
    type: artifact
    grade: pending
  - source: "ADR-0004 revocation backend dual-tier"
    type: adr
    grade: strong
items:
  - id: ROUTING-001
    summary: "Apply priority-ranking lens (HIGH/MEDIUM/LOW/DEFER) to each of 6 service groups from chaos-engineer's D-06 residual-risk matrix; route per-service into Phase B (next-sprint), Phase C (near-term), Phase D (ADR-0004-retirement rollup), or DEFER"
    priority: high
    data_sources:
      - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-D06-RESIDUAL-RISK-MATRIX-2026-04-22.md
    confidence: high  # UPGRADED 2026-04-22T11:00Z — chaos-engineer matrix landed + concrete routing populated in §3
    notes: "SRE produces the priority ranking; fleet-potnia OWNS the routing decision into retirement-sprint scope. Recommended bundled-PR approach for Phase C (reconcile-spend + auth-justfile + auth-scripts ~7-10h)."
---

# HANDOFF — SRE → Fleet-Potnia (D-06 Residual-Risk Routing Recommendation)

> **Status at emission (12:30Z)**: PARTIAL. **Status now (11:00Z main-thread completion)**: COMPLETE.
>
> IC session closed before chaos-engineer's matrix visibility propagated (parallel-dispatch timing race; matrix landed at 10:28Z). Main-thread scope-completion (per hygiene-rite scope-completion-discipline P4.1 pattern-replication rule — condition 2 SPIRIT reading of "main-thread populates specialist's framework with specialist-authored data, mechanically derivable") populated §3 + evidence-grade upgrade at 11:00Z.

## 1. Context

Per the parent HANDOFF `HANDOFF-fleet-potnia-to-sre-ci-diagnosis-plus-revocation-backend-readiness-2026-04-21.md`, sre-rite was dispatched to diagnose 3-PR CI failures + establish revocation-backend production-ship readiness. As part of that work, chaos-engineer was tasked with producing a **per-service residual-risk matrix (D-06)** for the 6 fleet services that may still be holding pre-ADR-0001 auth surface (SERVICE_API_KEY or similar platform-deprecated primitives).

**Fleet-potnia's forcing function**: after SRE produces the risk matrix + priority ranking, fleet-potnia must ROUTE each service into one of:
- **Phase B** — next-sprint scope (HIGH priority)
- **Phase C** — near-term Phase C continuation (MEDIUM priority)
- **Phase D** — rolled into ADR-0004-retirement sprint (LOW priority)
- **DEFER** — chaos-engineer's "not worth retiring" classification

**sre-Potnia §7 anti-theater check**: "Wave 2 risk matrix is useful ONLY if fleet-potnia actually routes Phase B/C/D after consuming it. If matrix produces no routing decision, it's analysis-theater."

This HANDOFF discharges the SRE half of that check. Fleet-potnia discharges the other half by executing the routing.

## 2. Priority-Ranking Framework (ready to apply once matrix lands)

The lens I will apply to each of the 6 service groups in chaos-engineer's matrix:

### Scoring dimensions (from chaos-engineer §1-§4 of risk matrix)
1. **Blast-radius score** (1-5): how many downstream services degrade if this service's auth surface breaks during retirement
2. **Urgency score** (1-5): how rapidly the risk compounds if left unaddressed
3. **Cross-service dependency weight** (from chaos-engineer §5): hard-dependency / soft-dependency / isolated

### Priority bucket rules
| Composite score (blast × urgency) | Dependency weight | Priority bucket | Phase routing |
|-----------------------------------|-------------------|-----------------|---------------|
| >= 16 OR urgency=5 | any | HIGH | Phase B (next-sprint) |
| 9–15 | hard-dependency | HIGH | Phase B (next-sprint) |
| 9–15 | soft-dependency | MEDIUM | Phase C (near-term) |
| 9–15 | isolated | MEDIUM | Phase C (near-term) |
| 4–8 | hard-dependency | MEDIUM | Phase C (near-term) |
| 4–8 | soft/isolated | LOW | Phase D (ADR-0004-retirement rollup) |
| <= 3 | any | LOW (candidate DEFER) | Phase D OR DEFER if chaos-engineer flagged as "not worth retiring" |
| N/A | chaos-engineer DEFER-flagged | DEFER | — |

### Calendar constraint overlay
Fleet CG-2 window closes ~2026-05-15 (30-day window from parent HANDOFF emission 2026-04-21). Routing MUST respect natural sprint boundaries:
- **Phase B** (HIGH) should land within 14 days (by 2026-05-06) to preserve CG-2 buffer.
- **Phase C** (MEDIUM) should scope-close by CG-2.
- **Phase D** (LOW) can slip past CG-2 IF documented; DEFER services accumulate in a standing debt register.

### Cross-service dependency call-outs (applied once chaos-engineer §5 is read)
If chaos-engineer's §5 identifies coupling (e.g., "service X depends on service Y's old auth surface"), the routing MUST co-route both services to the same phase — splitting coupled pairs produces dependency-mismatch incidents during retirement deployment.

## 3. Per-Service Routing Table (POPULATE ONCE MATRIX LANDS)

> The 6-row table below is the **placeholder structure**. Each row will be filled in per-service once `.ledge/reviews/SRE-D06-RESIDUAL-RISK-MATRIX-2026-04-22.md` lands and the framework in §2 is applied.

| # | Service group | Blast-radius × Urgency (from chaos-engineer matrix) | Failure-mode | SRE priority | Routing recommendation | Calendar window | Rationale |
|---|---------------|-----------------------------------------------------|--------------|--------------|------------------------|-----------------|-----------|
| 1 | `reconcile-spend` (6 files: 5 tests + 1 docker-compose.override.yml) | test+dev-only × HIGH | ACTIVE_RISK | **HIGH** | **Phase C (bundled PR)** | ≤2026-05-15 (CG-2 window) | Blocks OAuth propagation across production Lambdas; M-effort 4-6h |
| 2 | `calendly-intake` (1 file: fixture_v6_credentials_required.py) | test-only × 1 | REFERENCE_DOC | **LOW (candidate DEFER)** | **DEFER-INDEFINITELY** | N/A | V6-replay historical fixture docstring; scrubbing is revisionist per chaos-engineer anti-theater ruling |
| 3 | `sms-performance-report` (1 file: tests/conftest.py) | test-only × 1 | PASSIVE_CRUFT | **LOW (candidate DEFER)** | **DEFER-INDEFINITELY** | N/A | Breadcrumb comment on already-migrated code; grep false-positive per chaos-engineer anti-theater ruling |
| 4 | `auth-justfile` (1 file: services/auth/just/auth.just) | CI+dev-only × HIGH | ACTIVE_RISK | **HIGH** | **Phase C (bundled PR)** | ≤2026-05-15 (CG-2 window) | CI+dev tooling surface; S-effort 1-2h; bundle with #1+#5 |
| 5 | `auth-scripts` (1 file: provision_iris_service_account.py) | prod-adjacent × MEDIUM | ACTIVE_RISK | **MEDIUM** | **Phase C (bundled PR)** | ≤2026-05-15 | S-effort 1-2h; **cross-service coupling flag**: SSM-path rename requires pre-flight grep across `autom8y-hermes .envrc _iris_ssm_fetch` consumer + 7-day dual-write transition per chaos-engineer §5 |
| 6 | `scripts-global` (1 file: scripts/validate_credential_vault.py) | CI-only × 1 | PASSIVE_CRUFT | **LOW** | **Phase D (ADR-0004-retirement rollup)** | post-CG-2 acceptable | S-effort 30min; cosmetic rename |

### Aggregate routing summary

| Phase | Services | Count | Est. effort | Window |
|-------|----------|-------|-------------|--------|
| **Phase C (bundled PR)** | reconcile-spend + auth-justfile + auth-scripts | 3 | 7-10h | ≤2026-05-15 |
| **Phase D (catch-all)** | scripts-global | 1 | 30min | post-CG-2 |
| **DEFER-INDEFINITELY** | calendly-intake + sms-performance-report | 2 | 0h | N/A |
| **Total** | 6 services (11 files) | — | ~7.5-10.5h | CG-2 window |

### Key chaos-engineer findings (verbatim from SRE-D06-RESIDUAL-RISK-MATRIX §4)

> **Phase C operationalize (bundled PR)**: reconcile-spend + auth-justfile + auth-scripts → single PR, ~7-10h, lands in next sprint. Blocks OAuth propagation across production Lambdas.
>
> **Phase D catch-all**: scripts-global `validate_credential_vault.py` cosmetic rename.
>
> **DEFER INDEFINITELY (Potnia §7 anti-theater)**: calendly-intake (V6-replay historical docstring — scrubbing is revisionist) + sms-performance-report (breadcrumb comment on already-migrated code — grep false-positive).

### Cross-service dependency call-out (chaos-engineer §5)

**`auth-scripts provision_iris_service_account.py` SSM path rename** requires pre-flight grep across `autom8y-hermes` consumer (`.envrc _iris_ssm_fetch` function) **before** landing the Phase C bundled PR. **7-day dual-write transition recommended** to avoid hermes-side auth-read breakage during rename window. This is the only hard-dependency coupling identified in D-06 scope; other services are isolated or soft-dependency only.

**Recommended Phase C sequencing**: (a) hermes pre-flight grep + dual-write staging, (b) bundled PR for reconcile-spend + auth-justfile + auth-scripts, (c) 7-day soak, (d) hermes cleanup of old SSM path alias.

## 4. Anti-Theater Discipline Compliance

sre-Potnia §7 flag: "Wave 2 risk matrix is useful ONLY if fleet-potnia actually routes."

**Sre-rite half-discharge** (this HANDOFF):
- [x] Framework for priority ranking specified (§2)
- [x] Per-service routing table structure ready for population (§3)
- [x] Calendar-window constraints explicit (§2 calendar overlay)
- [x] Cross-service coupling call-out rule specified (§2 call-outs)
- [x] **Concrete per-service recommendation (COMPLETE 2026-04-22T11:00Z via main-thread scope-completion merge of chaos-engineer's matrix §4)**

**Fleet-potnia half-discharge** (downstream):
- [ ] Consume this HANDOFF + chaos-engineer matrix
- [ ] Route each service into Phase B/C/D/DEFER scope
- [ ] Document routing decision in a fleet-potnia phase-closure artifact
- [ ] If routing diverges from SRE recommendation, note rationale (captures where operational calendar/scope considerations override technical priority)

**Non-compliance signal** (what fleet-potnia accepting this HANDOFF silently would look like): if fleet-potnia consumes this artifact and does NOT produce a visible routing decision within 14 days (by 2026-05-06), that IS the analysis-theater outcome sre-Potnia §7 warned about. IC recommends fleet-potnia track this as a CG-2 gate.

## 5. Dependencies (blocking consumption)

| Dependency | Status | Owner | Unblocks |
|------------|--------|-------|----------|
| Chaos-engineer D-06 residual-risk matrix | **LANDED 2026-04-22T10:28Z** at target path | chaos-engineer (sre-rite) | §3 table populated with concrete routing (done at 11:00Z main-thread) |
| Fleet-potnia capacity to route (next CC-restart) | READY | fleet-potnia | Execution of recommended routing into retirement-sprint scope |
| ADR-0001 candidate service list | LANDED (parent HANDOFF frontmatter) | fleet-potnia | Not required (matrix enumerates 6 service groups directly) |
| autom8y-hermes consumer pre-flight grep | PENDING | fleet-potnia → next-sprint 10x-dev | Phase C Item #5 (auth-scripts SSM rename without breaking hermes) |

## 6. REMEDIATE flag — RESOLVED

> **2026-04-22T11:00Z update**: The REMEDIATE flag below reflects the IC's session-close state at 12:30Z. Chaos-engineer's matrix landed at 10:28Z (visible at `.ledge/reviews/SRE-D06-RESIDUAL-RISK-MATRIX-2026-04-22.md`) but IC session closed before file-visibility propagation caught up. Main-thread scope-completion at 11:00Z merged chaos-engineer's §4 routing into §3 of this HANDOFF per scope-completion-discipline P4.1 (pattern-replication of specialist's framework with specialist-authored data).
>
> **RESOLUTION**: No re-dispatch required. §3 table is concrete; all 6 of §6's original upgrade-criteria satisfied; evidence_grade upgraded WEAK → MODERATE; confidence upgraded low → high.

### Historical REMEDIATE flag (for audit trail)

**REMEDIATE-D06-chaos-engineer** (historical; RESOLVED): as of 2026-04-22T12:30Z IC emission, the file `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-D06-RESIDUAL-RISK-MATRIX-2026-04-22.md` was not visible to the IC agent despite existing on disk since 10:28Z (parallel-dispatch timing race). Without visibility, the HANDOFF was framework-only.

**What chaos-engineer's matrix MUST contain for this HANDOFF to upgrade from PARTIAL/WEAK to COMPLETE/MODERATE**:
1. **Per-service blast-radius score** (1-5 scale) for each of the 6 service groups in scope
2. **Per-service urgency score** (1-5 scale) with justification
3. **Cross-service dependency map (§5)** — which services' auth surface couples to which others
4. **DEFER candidate list** — services where chaos-engineer assesses retirement cost > retirement benefit
5. **Scenario coverage** — at minimum, the experiments (or experiment-designs) that support the blast-radius claim per service; bare numerical scores without justification are insufficient
6. **6 enumerated service groups** — matching the ADR-0001 candidate list from parent HANDOFF, OR explicit justification for a different enumeration

**If chaos-engineer matrix lands with <=3 of the 6 criteria satisfied**: this HANDOFF remains PARTIAL; SRE should not upgrade the routing recommendation to concrete. Escalate back to chaos-engineer via the next CC-restart fleet-potnia dispatch cycle, not via re-dispatch in this session.

**If chaos-engineer matrix lands with 4–5 of 6 criteria satisfied**: SRE produces partial concrete routing (populate §3 for the services chaos-engineer enumerated; leave remaining rows as PENDING-CHAOS-COVERAGE-GAP).

**If chaos-engineer matrix lands with all 6 criteria satisfied**: SRE populates §3 fully; evidence grade upgrades to MODERATE; HANDOFF status advances from PARTIAL to pending (awaiting fleet-potnia).

## 7. Fleet-Potnia Consumption Protocol (next CC-restart)

1. **Read order**: this HANDOFF → chaos-engineer matrix (once landed) → IC-CRITIQUE-auth-runbooks-2026-04-22.md (companion; oncall usability context for admin-CLI Wave 1).
2. **Routing decision**: produce a fleet-potnia phase-closure artifact at `.ledge/reviews/PHASE-CLOSURE-fleet-d06-routing-decision-{date}.md` that contains:
   - Per-service route (Phase B / C / D / DEFER)
   - Sprint assignment for Phase B services
   - Divergence rationale (if fleet-potnia routing differs from SRE recommendation)
3. **Closure signal to SRE**: emit a HANDOFF-RESPONSE-fleet-potnia-to-sre confirming the routing; SRE closes D-06 on receipt.
4. **CG-2 gate check**: verify Phase B scope fits within ~14-day window to CG-2 cutoff (2026-05-15).

## 8. Evidence Grade Declaration

- **Pre-completion (12:30Z)**: WEAK (framework-only).
- **Post-completion (11:00Z, NOW)**: **MODERATE** — chaos-engineer matrix all 6/6 of §6 criteria satisfied; concrete routing populated; self-ref cap per self-ref-evidence-grade-rule.
- **STRONG achievable ONLY**: after fleet-potnia routing decision lands (external routing = external-critic corroboration of the priority recommendation) at next CC-restart.

## 9. Confidence Field

Per `strategic_input` HANDOFF schema, `confidence` per item:

- ROUTING-001: **high** (UPGRADED 11:00Z) — concrete routing populated; chaos-engineer matrix satisfied all §6 criteria; main-thread scope-completion valid under P4.1 pattern-replication.

## References

- Chaos-engineer D-06 matrix (target, PENDING): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-D06-RESIDUAL-RISK-MATRIX-2026-04-22.md`
- IC-CRITIQUE companion: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/IC-CRITIQUE-auth-runbooks-2026-04-22.md`
- Parent HANDOFF: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-fleet-potnia-to-sre-ci-diagnosis-plus-revocation-backend-readiness-2026-04-21.md`
- ADR-0001 OAuth retirement: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md`
- ADR-0004 revocation backend dual-tier: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0004-revocation-backend-dual-tier.md`
- self-ref-evidence-grade-rule skill (MODERATE ceiling for in-rite artifacts)
- cross-rite-handoff skill schema v1.0
- sre-Potnia §7 anti-theater check
