---
type: review
artifact: adversary-verdict-consolidation
initiative: asana-mcp-postfelt-hardening
date: 2026-07-20
scribed_by: dispatcher (session b3f74f84) — verbatim-faithful condensation
provenance: >-
  Five adversary verdicts rendered in-session 2026-07-20 by rite-disjoint critic
  seats (arch-adversary ×4 renders, pattern-profiler ×1) under the
  critic-substitution rule (change-warden / audit-lead seats absent this session).
  Full verbatim reports live in the session transcript (agent task records,
  session b3f74f84-cb83-44ab-9e73-e07868237df0). Scribed to disk so the PT-09
  eunomia receipts-only attestation has the verdict chain as artifacts.
evidence_ceiling: MODERATE
---

# ADVERSARY VERDICT CHAIN — asana-mcp-postfelt-hardening wave (2026-07-20)

Every verdict below is HEAD-BOUND: it applies to the named SHA only. Where a head
moved after a verdict, the record shows the re-gate. All discharge receipts are
{path} or command receipts reproducible from the repos.

## V1 — a8 PR #104 (fleet startPeriod clamp) — arch-adversary

- **Verdict: PASS-WITH-CONDITIONS @ 979d28f7** → merged 80402fd3 (squash --admin
  per operator FULL-DELEGATION ruling, AskUserQuestion 2026-07-20).
- Challenges: C1 no-op proof HELD (8 fleet consumers enumerated, grace ∈ {60,120};
  module born with the coupling at 718e38d — no pre-coupling pins exist);
  C2 jsonencode byte-identity HELD (tf 1.14.6 console probes); C3 successor
  fitness HELD; C4 fmt/parse HELD; C5 CI-sufficiency HELD-as-syntax-tier
  (named residuals: no rendered-taskdef golden test, no clamp-fires test).
- Conditions: **COND-1** successor must retain explicit
  `container_health_check_path = "/health"` → **DISCHARGED** (V2 §S1, diff +
  rendered-plan levels). **COND-2** empirical at successor apply → **DISCHARGED**
  (RegisterTaskDefinition accepted startPeriod=300 = taskdef :659 registered;
  WARMING task survived ≈29.5 min ≫ 390 s — PT-04 receipt, activation ledger).
- Advisory (carried to hygiene/eunomia): unclamped vendored twin at autom8y
  terraform/modules/platform/primitives/ecs-fargate-service/main.tf:166 — zero
  consumers; dead-code reap candidate.

## V2 — autom8y PR #1157 (TG→/ready flip + grace 2400 + ref bump + pins) — arch-adversary

- **Verdict: PASS-WITH-CONDITIONS @ fc29c6cb** → revised to clean PASS per its
  own pathway at merge-time check → merged d502398d.
- Challenges: S1 COND-1 **DISCHARGED at both levels** (diff: unchanged middle
  line of the contiguous hunk; rendered: CI plan artifact tfplan-asana-production
  probed directly — container healthCheck on localhost:8000/health, startPeriod
  300, image = pinned digest cb25a80a…1b685); S2 ref-bump exact (+1/−1 clamp
  only; 80402fd3 ancestor of a8 main); S3 plan = exactly the 4-resource expected
  set; S4 **DEVIATION-1 RULED ACCEPTABLE IN-PR** (first plan carried an 8-lambda
  image rollback from same-morning dispatch pin drift — the #1154 near-miss class
  realized; in-PR refresh-to-live cure two-sided-proven across plan runs
  29751711445/29752109697; separation would create an ordering hazard);
  S5 pin-race named as merge-time condition; S6 grace semantics HELD (two
  independent survival layers).
- Merge-time condition (S5): **DISCHARGED by dispatcher** — live read immediately
  pre-merge: PRIMARY taskdef :658, main container image tag 2ee3391 (two
  read-only AWS calls; no dispatch raced the pin).
- DEVIATION-2 (blue-TG target_health_state fill-in): verified pre-existing
  reconcile noise (pre-PR run 29743179824), NOT condition-material.

## V3 — autom8y-asana PR #249, iteration 1 (sidecar dual-key tags) — arch-adversary

- **Verdict: PASS-WITH-CONDITIONS @ 16cfbb64.**
- Challenges: C1 fences HELD ×4 (mcp/-only — src/ bit-identical to origin/main;
  zero new HTTP write verbs; 503-warming fence intact with planted-string teeth;
  no forbidden imports/literals); C2 PT-05 #1 honesty HELD (satellite contract
  gap reproduced from source: tag_service.py returns has_more=False for both
  miss and cap-truncation — truncation genuinely not machine-distinguishable);
  C3 PT-05 #2 mechanics HELD (cache TTL real, positives-only; 429 backoff
  bounded+typed) with negative-caching herd risk quantified as FLAG;
  C4 PLAY-2/PLAY-3 substance HELD with one gap (C-2 below); C5 test quality
  HELD (10 sampled, behavior-grade); C6 e2e receipt PARTIAL (three flags).
- Conditions: **C-1** e2e receipt cure (provenance line; [0]-anomaly
  investigation; idempotency demonstrated-not-asserted); **C-2** post-write
  `resp.json()` outside the soft-fail envelope — a 200-with-malformed-body
  read-back would crash after the committed write; **C-3** negative-resolution
  herd risk ticketed to the WS-B1 satellite follow-up.

## V4 — autom8y-asana PR #249, iteration 2 DELTA (2 of 2) — arch-adversary

- **Verdict: PASS @ b98936e7. Original C-1/C-2/C-3 all DISCHARGED; new issues
  from the delta: NONE.**
- D1 (C-2 fix) verified incl. exception-coverage probes (JSONDecodeError and
  UnicodeDecodeError both subclass ValueError; streaming edge unreachable;
  no raw-body leak in the detail string). D2 Retry-After 30 s cap verified inert
  on the default exponential path. D3 transcript cure verified with independent
  corroboration — the old transcript's own `has_more:false` metadata proved the
  original [0] was a name query (impossible for a bare page-1 of a >100-tag
  workspace), retiring the smells-trimmed concern; idempotency demonstrated
  (2×POST 200, read-back count=1). D4 herd-risk ticket present in PR body.
  D5 fence re-sweep clean; CI spot-verified.
- Post-verdict: head moved to cb51833b via update-branch (4 substrate-arc
  commits landed on main); dispatcher delta-guard at merge verified mcp/
  identical to the verdict head → merged b630a901.

## V5 — autom8y-asana PR #247 (WS-D knowledge/governance) — PT-07, pattern-profiler

- **Verdict: CONCUR-WITH-CONDITIONS @ a44b78aa.**
- Dimensions: K1 anchor validity — 20+ anchors sampled byte-exact across three
  verification channels; one finding K1-a (below). K2 honesty discipline CLEAN
  (operator's §5.2 verdict cited never paraphrased; UNATTESTED rows honest;
  two explicit self-corrections found and praised). K3 scar quality CLEAN
  (SCAR-TG-LIVENESS-001 CURED with history preserved; N=1 candidates not
  over-promoted; 3rd-strike claims corroborated). K4 defer-watch schema CLEAN
  (17 entries). K5 single-writer + append-only CLEAN (dossier ratified text
  byte-identical to main). K6 ledger coherence CLEAN (5/5 spot-checks).
- Condition **K1-a**: the critic's designated ground-truth checkout (the
  operator's primary main ref) is frozen at f3d8eec1 — pre-epic — and
  structurally could not corroborate the wave's merge SHAs. **DISCHARGED by
  dispatcher 2026-07-20**: 9/9 wave merge SHAs (23440991, edaa9ddd, a0b7142d,
  793e670b, beaf3344, 2eb830ca, 6edc83d5, 2ee3391c, b630a901) verified
  `git merge-base --is-ancestor` of freshly-fetched origin/main (tip b630a901).
  Recorded in-tree at the telos attestation comment (s5 micro-pass 53e408ff,
  with s5's own ×9 re-check).
- Post-verdict: merge micro-pass (update-branch edb72a8e + single-writer
  WS-B2→LANDED commit 53e408ff) → merged b0cb45f0.

## Chain summary for PT-09

| PR | Verdict head | Verdict | Conditions | Merge |
|---|---|---|---|---|
| a8 #104 | 979d28f7 | PASS-W-C | COND-1 ✓ COND-2 ✓ | 80402fd3 |
| autom8y #1157 | fc29c6cb | PASS-W-C → PASS | S5 merge-time ✓ | d502398d |
| asana #249 (i1) | 16cfbb64 | PASS-W-C | C-1/C-2/C-3 → i2 | — |
| asana #249 (i2) | b98936e7 | PASS | all discharged | b630a901 |
| asana #247 (PT-07) | a44b78aa | CONCUR-W-C | K1-a ✓ | b0cb45f0 |

Self-attestation note: this consolidation is dispatcher-scribed and therefore
caps at MODERATE; the underlying verdicts were rendered by rite-disjoint seats.
STRONG on this chain arrives only via the PT-09 eunomia attestation.
