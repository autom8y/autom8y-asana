---
type: handoff
status: accepted
from: review
to: 10x-dev, sre, know, iris
created: 2026-06-24
initiative: asana-cutover-readiness-sequencing
adjudicated_by: operator
---

# Adjudicated First-Wave Execution Plan — autom8y-asana cutover-readiness

> **GRANDEUR ANCHOR:** Pick up the torch on autom8y-asana — the ecosystem's CRM-UI / datastore-frontend / workflow-orchestration layer and an optimizing-decomposition of the `../../../autom8` legacy monolith (`/Users/tomtenuta/code/autom8`) — by advancing SCAR-REG-001 and SCAR-IDEM-001 from authored toward proven; proven ONLY by a live receipt, never a green dashboard or optimistic merge. Production-mutating levers stay the user's.

**Entry state (proven live at HEAD `f4f924d2`):** `.ledge/reviews/asana-coherence-case-file.md` (grade C, both blockers BLOCKED), `.ledge/reviews/asana-coherence-critic-verdict.md` (rite-disjoint CONCUR-WITH-FLAGS), `.ledge/reviews/PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md`, shape `.sos/wip/frames/asana-cutover-readiness-sequencing.shape.md`.

**North-star:** PROD-READINESS-FOR-CUTOVER (correctness + observability + coherence; on-prod but low-traffic, legacy monolith still carries most traffic). NO traffic move this cycle.

**Adjudicated sequencing:** **HYBRID** (operator ruling). **PR bar (Prescribed, every PR):** RED-first + critic-clean — a deliberately-broken fixture fires RED on the defect path (two-sided teeth: a no-defect variant passes GREEN), green after, rite-disjoint external critic verdict clean. No bandaids. Work in isolated worktrees off fresh `origin/main` (NOT on `chore/bump-core-4.6.0`). Never stage `.claude/ .gemini/ .knossos/ .know/ .mcp.json .gitignore`.

---

## H-1 DUAL-ANCHOR DESIGN (load-bearing — read before W-REG)

SCAR-REG-001's correct fix is a **JOIN, not a GID-match**:
- The legacy monolith holds the **section name→bucket taxonomy** (source-of-truth): `BusinessUnits.SECTIONS` at `/Users/tomtenuta/code/autom8/apis/asana_api/objects/project/models/business_units/main.py:18-39`, bound to `PROJECT_GID="1201081073731555"`. Buckets: `active{Month 1, Consulting, Active}`, `activating{Onboarding, Implementing, Delayed, Preview}`, `inactive{Unengaged, Engaged, Scheduled, Paused, Cancelled, No Start}`, `ignore{Templates}`. It **hardcodes NO GIDs** — resolves names→GIDs at runtime (`…/objects/section/main.py` `request_sections_for_project`).
- The **raw GIDs live ONLY in live Asana** (the iris READ of `GET /projects/1201081073731555/sections`).
- **Therefore:** rebuild `src/autom8_asana/reconciliation/section_registry.py:94-150` by joining `live-GID (iris) × name→bucket (monolith) → corrected frozensets`. A GID-match-only fix re-introduces the silent miscategorization that IS the scar. (Reconcile the monolith taxonomy against the in-code `EXCLUDED_SECTION_NAMES`/unit names — note the monolith `ignore` set is `{Templates}` only, vs the in-code EXCLUDED `{Templates, Next Steps, Account Review, Account Error}`; surface any divergence as a finding, do not silently pick one.)

---

## Wave plan (Hybrid)

### Wave 1 — open in parallel
**W-OBS** (10x-dev · asana-local · zero-dep · ~30 min · NO blocker):
- Add `emit_metric("StatusPushSkipped")` (or success/failure pair) at the gate-exit paths in `src/autom8_asana/services/gid_push.py:498-504` (the `AUTOM8Y_DATA_URL`-absent early-return at ~:503), closing the silent blind spot where the push-seam returns `False` with only a warning and no CloudWatch metric.
- **RED-first fixture:** with `AUTOM8Y_DATA_URL` absent, assert `StatusPushSkipped` fires; the no-defect variant (env present) does NOT fire. This is the two-sided teeth.
- Rationale: instruments the system so every later fix lands where regressions are visible; it is the case file's own step-1.

**W-IRIS route-build** (rite pantheons, operator-driven · longest/uncertain pole — start first to absorb latency):
- H-1's live receipt is BLOCKED-on-auth: no token-safe iris→Asana route exists; the PAT (`autom8y/asana/asana-pat` in Secrets Manager) is Lambda-runtime-only (`client.py:749` `AuthProvider.get_secret`).
- **Route spec:** stand up a read-only `autom8-asana-*` Lambda (or equivalent server-side S2S surface) that calls `AuthProvider.get_secret("ASANA_PAT")` → `GET /projects/1201081073731555/sections` and returns `name→GID`. iris then diffs that live map against the in-code `EXCLUDED_SECTION_GIDS`/`UNIT_SECTION_GIDS` frozensets. **READ-only**; the live section-GID WRITE and the Secrets-Manager grant/deploy are user-sovereign.
- Output rung: advances H-1 from `proven-in-code-only` → `proven` ONLY on the pasted live diff. Until the route lands, H-1 stays honestly BLOCKED (G-RUNG: do not round up).

### Wave 2 — after Wave 1 lands
**W-IDEM** (10x-dev · asana-local · correctness blocker):
- Fix `src/autom8_asana/api/middleware/idempotency.py:719` — `finalize()` exception swallowed under `except Exception # noqa BLE001`, so the idempotency key is not persisted and an S2S retry re-executes the mutation. Promote to an error metric + propagate per the ADR-omniscience-idempotency §3.7 intent (do not merely log).
- **RED-first fixture:** simulate a `finalize()` failure on a strict-once S2S path and assert the mutation executes TWICE (RED) under current code; the fixed variant executes once / surfaces the error (GREEN). Two-sided.

**W-LEGACY-ANCHOR read → W-REG** (legacy READ → 10x-dev write; GATED on W-IRIS receipt + legacy read):
- Read the monolith taxonomy (above), obtain the live-GID receipt (W-IRIS), then rebuild `section_registry.py:94-150` via the dual-anchor join. **RED-first fixture:** a section-name whose live GID differs from the frozen placeholder routes to the WRONG bucket under current code (RED); routes correctly post-fix (GREEN).

### Wave 3 — forks (iris READs + decision)
**W-FORK1** (`/v1/query` retire-vs-extend): run CloudWatch **Logs Insights** over the API log group, `filter @message like /deprecated_query_endpoint_used/` since 2026-06-01, aggregate `count(*)` + `count_distinct(caller_service)`. **G-DENOM gate:** retire is licensed ONLY if `recordsScanned > 0` (denominator real) AND distinct callers = 0; else extend/instrument-first. Pythia FORK-1 recommends **instrument-first**. Successor `/rows` route already live.
**W-BRIDGE** (M-4): query `Autom8y/AsanaBridgeFleet` across ALL dimensions (only `{staging, insights-export}` observed; `LastSuccessTimestamp` frozen 2026-06-18T13:32:06Z) to disambiguate idle-vs-telemetry-gap; route alarm to sre.

### Wave 4 — coherence (parallel, independent)
**W-KNOW** `/know --all` (P5: 90-commit drift + undocumented cache features) + defer-watch dispositions. **W-DOCS** correct interop figure `~30%`→`~14% (2/14)` at `protocols.py:42` + recover/flag the absent `INTEGRATE-ecosystem-dispatch §1.4` ref (`protocols.py:44`). **W-HYG** annotate the 10 unannotated broad-except sites (185/197 already annotated).

### DEFER (watch-registered — NOT this cycle)
**W-DEFER:** H-4 `cache_warmer.py` (1437 LOC) decomposition; FORK-2 interop shared-substrate PR into `autom8y_client_sdk.data` (cross-repo coordination, **deadline 2026-09-29**, G-PROPAGATE: belongs in the shared substrate, not a per-service orphan). Also lapsed-deadline reconciliation (EC-013 2026-05-11; TRADE-008 2026-06-01; defer-watch 2026-05-29) → routed to W-KNOW.

---

## Per-finding legacy-anchor rulings (from the shape §3)
- **H-1** = SOURCE-OF-TRUTH for name→bucket taxonomy, NOT a GID source (join design above).
- **H-2, H-3, H-4, FORK-1, M-4** = DEPRECATED-DIVERGE (modern-ecosystem constructs the monolith lacks; autom8y defines the target).
- **FORK-2** = MIXED — SDK substrate (`autom8y_client_sdk.data`) is source-of-truth; monolith diverge.
- **P5 / `.know`** = N/A, autom8y-asana-local.

## Rite switch (operator action — restart CC to enter the build pantheons)
1. `ari sync --rite=10x-dev` → restart CC → drive Wave 1–2 (W-OBS, W-IDEM, W-REG) via the 10x-dev pantheon (potnia, requirements-analyst, architect, principal-engineer, qa-adversary), worktree+PR, RED-first + critic-clean.
2. For W-IRIS / W-BRIDGE / W-FORK1: the iris + sre pantheons (operator-driven per adjudication) build the read-only Asana route and run the CloudWatch/Logs-Insights probes.
3. `/frame` or `/sprint` against this plan + the shape at sprint start. Each sprint's exit gate binds a rite-disjoint critic (G-CRITIC).

## User-sovereign levers (surface as commands; agents MUST NOT execute)
Merges to `main`; prod apply (Lambda/IaC); paging-alarm arming; deploy-freeze; token rotation (Asana PAT, `AUTOM8Y_DATA_API_KEY`, webhook inbound token); rollback; the live Asana section-GID WRITE; the Secrets-Manager grant for the W-IRIS read route.
