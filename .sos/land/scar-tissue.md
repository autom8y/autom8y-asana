---
domain: "scar-tissue"
generated_at: "2026-04-28T20:00:00Z"
expires_after: "14d"
source_scope: [".sos/archive/**", ".sos/sessions/**"]
generator: "dionysus"
source_hash: "8c58f930"
confidence: 0.80
format_version: "1.1"
sessions_synthesized: 10
last_session: "session-20260428-004041-4c69f12c"
provenance_distribution:
  wrapped: 10
  stale_parked: 0
  recent_parked: 0
sails_color: "WHITE"
sails_reason: "10 RICH/MODERATE WRAPPED sessions feed this domain; newest <24h old; explicit blocker telemetry remains sparse, hence -0.05 from HIGH ceiling"
---

## Blocker Catalog

| Session | Blocker | Resolution | Domain |
|---------|---------|-----------|--------|
| session-20260303-134822-abd31a5b | S3 fast-path bypasses cascade validation -> office_phone null -> NOT_FOUND for 9/10 accounts on POST /v1/resolve/unit | WS-2 + WS-1 (Phase A) — cascade validation on S3 fast-path; subsumed into 2026-03-15 production-api-triage | resolver/cascade |
| session-20260303-134822-abd31a5b | EntityWriteRequest lacks extra="forbid" -> unknown fields silently dropped | WS-3 standalone commit (planned) | api-contracts |
| session-20260315-131104-fd8bf8d4 | AUTOM8_DATA_API_KEY env var typo -> production API auth failures | WS-2 sprint-1 fix to AUTOM8Y_DATA_API_KEY | env-config |
| session-20260315-131104-fd8bf8d4 | CascadingFieldResolver 30% null rate on units | WS-1 sprint-2 fix (ADR-cascade-null-resolution.md) | dataframes/cascade |
| session-20260326-005612-0ff2c860 | Offer office column source=None bypasses cascade contract — 30-40% null rate | WS-2 cascade contract repair (3 source changes, 28/28 tests pass) | dataframes/offer |
| session-20260326-005612-0ff2c860 | PhoneNormalizer (E.164) wired only into matching engine, not read path -> reconciliation blindness on (office_phone, vertical) | WS-3 PhoneTextField + cascade guard (2,859 tests) | dataframes/normalizers |
| session-20260409-170809-a07b979e | UnicodeEncodeError in middleware/transport blocking Schemathesis fuzz suite | Fixed; respx mocks introduced; pass rate 5%->66% | api/middleware |
| session-20260415-010441-e0231c37 | xdist worker crashes in test_workflow_handler.py and test_openapi_fuzz.py (commit d0a6335b disabled xdist) | Sprint-1 cartography pending; root-cause not yet attributed | test-infrastructure |
| session-20260415-010441-e0231c37 | Consumer-gate poll timeout raised from 900s to 2400s (commit 15a51b24 in autom8y repo) due to autom8y-asana wall-clock | asana-test-rationalization initiative spawned (parked, succeeded by project-crucible) | ci/timing |
| session-20260427-154543-c703e121 | metrics CLI silently under-counts: ~22 active sections expected, only ~6 in parquet | 4 open questions still unresolved at park; bucket-mapping verification needed | observability/metrics |

## Rejected Alternatives

| Session | Decision | Rejected | Rationale |
|---------|---------|----------|-----------|
| session-20260315-131104-fd8bf8d4 | AUTOM8Y_DATA_API_KEY (corrected) | AUTOM8_DATA_API_KEY (legacy typo) | Typo caused production API auth failures |
| session-20260326-005612-0ff2c860 | Cascade contract for Offer office field | Raw extraction without cascade governance | source=None bypassed cascade contract -> 30-40% null rate |
| session-20260326-005612-0ff2c860 | PhoneTextField with E.164 on read path | PhoneNormalizer only in matching engine | Read-path lacked normalization -> reconciliation blindness on phone join key |
| session-20260329-153238-9bcc549e | P3-A stub field removal (Necessity 2 test hygiene) | Keeping stale stub-field assertions | Tests assert against fields removed in P3-A; commit 9d279a2 updates assertions |
| session-20260409-170809-a07b979e | Numeric regex GID validation + Literal types for schema names | Loose string GID validation | Schemathesis fuzzing exposed weak validation; tightened to numeric regex |
| session-20260415-032649-5912eaec | Parametrize campaign over fixture proliferation | Local-fixture explosion (86.8% local fixture ratio) | Parametrize rate 0.90% -> >=8% target; coverage floor >=80% non-negotiable |
| session-20260427-232025-634f0913 | Defer touching cascade-spike sessions (session-20260303-173218, 134822) | Unparking adjacent scar-tissue sessions | Explicitly marked "Not a prerequisite. Do not unpark or interfere." |

## Friction Signals

- **Recurring**: Patterns across 2+ sessions
  - CascadingFieldResolver null rates: seen in session-20260303-173218 (30% units), session-20260315 (30% null rate fix), session-20260326 (30-40% Offer office null)
  - Cascade-contract bypass on fast-paths: seen in session-20260303-134822 (S3 fast-path), session-20260326 (Offer source=None)
  - Test-suite scale/speed friction: seen in session-20260415-010441 (13,264 tests, xdist disabled), session-20260415-032649 (project-crucible: 13,072->12,320 tests, coverage 87.59%, CI <60s target)
  - Stale-cache observability gaps: seen in session-20260326 (display null audit), session-20260427-154543 (parquet freshness varies, no SLA, 22-section coverage gap)
  - SCAR test cluster preservation: explicit in session-20260415-032649 (33 inviolable scar tests: SCAR-001/005/006/010/010b/020/026/027/S3-LOOP, TENSION-001)
  - Early-exit at requirements phase: 9/18 sessions parked at requirements without artifact production
- **One-time**: Isolated friction events
  - LocalStack S3 bucket empty -> 0/7 project cache warming failure: session-20260302-165404
  - UnicodeEncodeError in middleware/transport blocking fuzz suite: session-20260409
  - autom8y-asana identified as fleet's binding CI constraint forcing 2400s consumer-gate timeout: session-20260415-010441
  - WS-gamma stash (pre-WSgamma-asana-drift-150files) unaddressed, 150-file drift: session-20260415-010441
  - 2 STALE_PARKED occupants in .sos/sessions/ duplicate WRAPPED archive entries (session-20260303-134822, session-20260303-173218): naxos hygiene flag

## Quality Friction (Sails Analysis)

| Sails Color | Sessions | Common Failure Proofs |
|------------|---------|---------------------|
| GRAY | 17 | All proofs UNKNOWN — no CI proof pipeline wired into WHITE_SAILS |
| BLACK | 1 | session-20260409 (Schemathesis remediation): all proofs UNKNOWN but base BLACK — likely manually downgraded due to incomplete coverage at archive |

Total: 18/18 (100%). 0 WHITE proofs across all 18 sessions confirms WHITE_SAILS log pipeline is not active.

## Deferred Work

- FQ write hardening (WS-4): started in session-20260315, sprint-3 exit artifact pending at archive
- Reconciliation investigation (WS-3): started in session-20260315, sprint-4 exit artifact pending at archive
- Architecture Review: Data Attachment Bridge (session-20260318): parked at requirements, no follow-up observed across remaining 14 sessions
- asana-api-docs-excellence: 2 attempts (session-20260324-131439 + 134959), both parked at requirements, no resolution observed
- release-gating-readiness (session-20260325): parked at requirements, no follow-up observed
- LocalStack S3 cache seeding spike (session-20260302): parked at research, no follow-up
- N8N-CASCADE-FIX (session-20260303-134822): WS-3/WS-4/WS-5 (Phases B/C/D) deferred; superseded by production-api-triage initiative
- asana-phantom-materialization (session-20260329): Sprints 2/3/4 (N4 OFFER_CLASSIFIER, N1 Reconciliation, N3 Vertical Backfill) pending
- eunomia-asana-test-remediation (session-20260412): parked at requirements; succeeded by asana-test-rationalization 3 days later
- ADR-offer-office-cascade-contract.md (session-20260326): listed as pending in artifacts; finalization status unverified
- active_mrr provenance (session-20260427-154543): 4 open questions unresolved (bucket mapping, freshness SLA, section coverage gap, staleness-surface decision)
- project-asana-pipeline-extraction Phase 0 spike handoff (session-20260427-232025): pending at park
- project-asana-pipeline-extraction-phase1 (session-20260428): PRD/TDD pending at park; telos_deadline 2026-05-11

## Confidence Notes

- Confidence 0.80 (HIGH tier 0.85, -0.05 for sparse explicit-blocker telemetry — most blockers extracted from initiative narratives rather than dedicated Blockers sections)
- 10/18 sessions classified RICH or MODERATE feed this domain; 8/18 SPARSE excluded per spec
- 8/10 RICH/MODERATE sessions report "None" or "None yet" under explicit Blockers — friction extracted from Scope/Initiative-Summary/Sprints/Investigation-Context narratives
- No agent.delegated events available in this dispatch (events.jsonl read not performed in this synthesis cycle); rejected-alternatives extracted from frame/shape/PRD references
- Cascade-related friction is the dominant recurring scar across the corpus (3 distinct sessions, 2 distinct manifestations)
- Test-infrastructure friction is the second-most-recurrent theme (xdist crashes, fixture explosion, scar-test preservation)
