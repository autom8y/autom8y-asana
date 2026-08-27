# Structure Evaluator Memory

## Assessment Patterns
- Always perform the false-positive check BEFORE classifying as anti-pattern. Many patterns that look wrong are intentional trade-offs.
- The autom8y-asana codebase has extensive ADR documentation. Check for ADR references before flagging design decisions.
- Use dependency-map coupling scores and topology classifications as primary evidence. Supplement with targeted code reads for specific lines/logic.
- Risk register leverage scoring: impact / effort. Quick wins are high-leverage, long-term transformations are necessary-but-low-leverage.
- [Central-arbiter SPOF verdict — fail-posture reframe](f1a-arbiter-spof-verdict.md) — strictly-worse is a fail-posture (open/closed) question, not in-path-vs-advisory topology; fail-open has two non-equivalent flavors (revert-to-storm vs preserve-floor). Points to the F1a node-3c assessment.
- [RD audit-line landing grid](rd-audit-line-landing-grid.md) — fleet-delegation-phase2: R28 audit-LANDING vs species-CONSUMPTION split; real live audit path = 5-member per-route log family (workflows/entity_write/intake_create/intake_custom_fields/receipts), not the dormant S2SAuditLogger.
- [Discriminating-canary CP-3 grading](discriminating-canary-cp3-grading.md) — how to grade a Mode-1 canary CI PR: empty-production-diff G-THEATER tell, rc==1-EXACTLY teeth, JOB-level (not step-level) two-sidedness, mcp-island local-run needs fastmcp.
- [Substrate-v2 doctrine home + P11 gotcha](substrate-v2-doctrine-home.md) — RC-A..F fleet constitution lives at `.ledge/decisions/CONSTITUTION-substrate-invariants-*` (NOT charter P11's falsified `.a8/knossos`); construction-first + 4 sparing teeth; inheritance via S10 kit.
- [Adoption-by-reference critic recipe](adoption-by-reference-critic-recipe.md) — how to R31-critique a sibling's charter adoption-BY-POINTER stub: 0-shared-5-gram transcription check, resolver-from-canonical-root (worktree trap), fence_marker byte-exact, pin-landing; +2 durable flags (frontmatter pre-inscribing critic CONCUR; local-un-refusal ≠ fleet-gate loosening). Recurs via S10-kit propagation.
- [Rail-inventory critic recipe](rail-inventory-critic-recipe.md) — never accept a symbol grep as class-absence nor a decorator as its gate: enumerate writes via the `x-fleet-side-effects` marker, walk route→service→client, check RouterMount, separate authn from authz.
- [OpenAPI contract-drift gate](openapi-contract-drift-gate.md) — response-boundary critique: "reaches the wire" (emitted body) ≠ "reaches the published `openapi.json`"; the committed-vs-generated drift check (`generate_openapi.py --check`) is NOT in blocking CI (only `validate_openapi.py`, structure-only). Additive response fields can ship a stale published contract. First hit: EX-3.
- [NR-4 ASR generation-provenance sweep](nr4-asr-generation-provenance-sweep.md) — the hop-one-past map for the 5-of-5 false-negative: delivery chain is LIVE (report_posted), 4 obtainable authorship candidates (whole-service grep/verdict-store/completion-event/side-effect) all wrong-construct; discharge = EX-5 report_generated; watch report_posted has no content_hash.
- [S-09 W-F critique recipe](s09-wf-asana-critique-recipe.md) — 3 reusable moves: pristine-RED via `git archive` + PYTHONPATH shadowing (worktree venvs are EMPTY here); `model_serializer(mode="wrap") -> dict[str,Any]` ERASES the serialization JSON-schema (drop the annotation to fix); terraform env-wiring sweep for other default-ON legs on the same var (gid_push has 3).
- [Pristine-RED shadowing traps](pristine-red-shadowing-traps.md) — asana needs PYTHONPATH (editable install shadows the archive); calendly-intake needs an IN-TREE mutant (`pythonpath=["src","tests"]` in pyproject beats PYTHONPATH → false-GREEN); grade calendly-intake by node-ID set diff, never absolute pass-counts (62 pre-existing env failures).
- [CC-1 swap-detector NCSR recipe](cc1-swap-detector-ncsr-recipe.md) — how to adversarially re-derive a RED/GREEN swap-detector closure: pristine-RED via `git archive` to scratchpad (no checkout, fence-safe), false-RED discriminators (count-preserving + verdict-not-crash), two-residual grading (frozen-wire-token over-claim STANDS as fail-side label; hashless-live-emitter NARROWS to built-dark-not-live). Same telos as NR-4.
- [S-05 live-attestation recipe](s05-live-attestation-recipe.md) — attesting a live AWS landing own-hands: the wrong-namespace false-negative (empty `list-metrics` ≠ absence), EventBridge `TriggeredRules` is dead → instrument the TARGET + use a log-group-target rule as bus positive control, and the per-Lambda-version natural A/B (organic retry straddling a one-commit deploy).

## autom8y-asana Cache Subsystem
- Two independent tier systems: Entity Cache (Redis+S3) and DataFrame Cache (Memory+S3). Intentionally divergent per ADR-0067 (12/14 dimensions).
- SaveSession CacheInvalidator does NOT invalidate DataFrameCache (System B). MutationInvalidator DOES for structural mutations. This asymmetry is a key finding.
- LKG_MAX_STALENESS_MULTIPLIER = 0.0 means unlimited staleness (availability-first philosophy).
- `clear_all_tasks()` SCAN pattern `asana:tasks:*` matches ALL entity types except DATAFRAME (which uses `asana:struc:*`).
- Derived timeline cache: 300s fixed TTL, no upstream invalidation.
- Two coalescing systems (DataFrameCacheCoalescer + BuildCoordinator) -- incremental migration per ADR-BC-002.

## File References
- Cache assessment: `.claude/wip/SPIKE-CACHE-ARCH/ASSESSMENT-CACHE.md`
- Cache topology: `.claude/wip/SPIKE-CACHE-ARCH/TOPOLOGY-CACHE.md`
- Cache dependencies: `.claude/wip/SPIKE-CACHE-ARCH/DEPENDENCY-CACHE.md`
