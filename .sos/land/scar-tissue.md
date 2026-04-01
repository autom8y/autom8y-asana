---
domain: "scar-tissue"
generated_at: "2026-03-29T00:00:00Z"
expires_after: "14d"
source_scope: [".sos/archive/**"]
generator: "dionysus"
source_hash: "905fe4b"
confidence: 0.55
format_version: "1.0"
sessions_synthesized: 8
last_session: "session-20260326-005612-0ff2c860"
---

## Blocker Catalog

| Session | Blocker | Resolution | Domain |
|---------|---------|-----------|--------|
| (none) | No blockers recorded in any session | N/A | N/A |

## Rejected Alternatives

| Session | Decision | Rejected | Rationale |
|---------|---------|----------|-----------|
| session-20260315-131104-fd8bf8d4 | Env var naming: AUTOM8Y_DATA_API_KEY | AUTOM8_DATA_API_KEY (previous) | Typo in original env var name caused production API auth failures |
| session-20260326-005612-0ff2c860 | Cascade contract for Offer office field | Raw extraction without cascade governance | source=None bypassed cascade contract, causing 30-40% null rate |
| session-20260326-005612-0ff2c860 | PhoneTextField with E.164 on read path | PhoneNormalizer only in matching engine | Read path lacked normalization, causing reconciliation blindness on phone join key |

## Friction Signals

- **Recurring**: Patterns across 2+ sessions
  - Session lifecycle complaints (moirai COMPLAINT files): seen in session-20260315-131104-fd8bf8d4, session-20260326-005612-0ff2c860
  - CascadingFieldResolver null rates: seen in session-20260315-131104-fd8bf8d4 (30% null), session-20260326-005612-0ff2c860 (30-40% null on Offer office)
- **One-time**: Isolated friction events
  - S3 bucket empty on LocalStack causing 0/7 project cache warming failure: session-20260302-165404-dfdf5ad1
  - Reconciliation endpoint failure requiring investigation: session-20260315-131104-fd8bf8d4

## Quality Friction (Sails Analysis)

| Sails Color | Sessions | Common Failure Proofs |
|------------|---------|---------------------|
| GRAY | 8 | All proofs UNKNOWN (no CI proof pipeline active) |

## Deferred Work

- FQ write hardening (WS-4): started in session-20260315-131104-fd8bf8d4, sprint-3 exit artifact pending
- Reconciliation investigation (WS-3): started in session-20260315-131104-fd8bf8d4, sprint-4 exit artifact pending
- Architecture Review: Data Attachment Bridge: parked at requirements in session-20260318-141031-485cc768, not seen completed in subsequent sessions
- asana-api-docs-excellence: attempted in 2 sessions (session-20260324-131439-602b6637, session-20260324-134959-b83800f2), both parked at requirements
- release-gating-readiness: parked at requirements in session-20260325-003123-fb6967fa, not seen in subsequent sessions
- LocalStack S3 cache seeding spike: parked at research in session-20260302-165404-dfdf5ad1, no follow-up session

## Confidence Notes

- Confidence below 0.7 due to absence of substantive blocker content in SESSION_CONTEXT files
- All 8 sessions report "None" or "None yet" under Blockers section
- No agent.delegated events found in any events.jsonl (agent routing decisions not tracked)
- Scar tissue signals extracted primarily from initiative narratives and file change patterns rather than explicit blocker/rejection records
- Friction signals are inferred from context (complaint files, null rate mentions) rather than structured blocker data
