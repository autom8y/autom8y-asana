# Principal Engineer Memory

## Pydantic Forward Reference Pattern (2026-02-23)

**Critical**: All model files in `src/autom8_asana/models/` use `from __future__ import annotations` with `NameGid` imported only under `TYPE_CHECKING`. This makes `NameGid` invisible at runtime. Pydantic v2 cannot resolve the forward reference string without `model_rebuild(_types_namespace={"NameGid": NameGid})`.

**Resolution locations**:
- `src/autom8_asana/models/__init__.py` -- resolves for application code paths
- `tests/conftest.py` `_bootstrap_session` fixture -- resolves for test code that imports directly from submodules

**Key insight**: `Task.model_rebuild()` propagates to ALL subclasses (BusinessEntity, Offer, DNA, etc.) automatically.

## Pre-existing Test Failures (2026-02-23)

~203 test failures are pre-existing and documented in `.wip/REMEDY-tests-unit-p1.md`:
- `test_routes_dataframes.py` (42 failures) -- API route changes not reflected in tests (422 vs 200)
- `test_client.py` (12 failures) -- httpx mock target issue (H-001 in remedy report)
- `test_contract_alignment.py` (21 failures) -- contract tests referencing wrong APIs
- Various other API route tests returning 422 instead of expected 200

These are NOT caused by RF-010/011/012 directory reorg. They predate those commits.

## Git Stash Warning

Using `git stash` + `git checkout <ref> -- tests/` + `git stash pop` leaves behind untracked files from the stash that won't be cleaned by `git checkout HEAD -- tests/`. Must manually remove stale files after stash pop. Avoid this pattern; use worktrees instead.

## Test Baseline

Current healthy baseline with model_rebuild fix: ~11,123 passed, ~203 failed, 46 skipped, 0 errors.
The "10,552 passed" baseline referenced in MEMORY.md predates the RF-008/009 adversarial test triage.

`tests/harness/substrate_gate tests/unit/substrate` scope baseline: 295 passed (post-#301, main 5d62d0b8); WU-3 iter-1 (PR #305) → 324; iter-2 dual-leg → 336.

## substrate-v2 `active_mrr` referent — CORRECTED by RULING-pythia-f305-1 (2026-08-04)

**SUPERSEDES my earlier 3-section note.** qa NO-GO'd WU-3 iter-1 (F-305-1); pythia ruled `active_mrr` DENOTES the **production-served number**, NOT the 3-section exemplar sum. The gate is a DUAL-LEG ledger (ruling Option (c)):
- **LEG A (the gate anchor, what PT-03 Q1 + auto-flip hang on)** = the served-definition active_mrr: 22-section OFFER classifier active set (`activity.py:181-208`) + dedup by `(office_phone, vertical)` keep="first" + `mrr>0` filter + Float64 sum (`offer.py:20-43` / `compute.py:66-116`). Build it by REUSING the real metric machinery: `compute_metric(MetricRegistry().get_metric("active_mrr"), frame)` then `.sum()` — this satisfies the ruling's §6 #1-7 by construction (classifier-sourced, never a hardcoded list). Requires columns `(section, mrr, office_phone, vertical)` present (offer schema `offer.py:19/28` confirms them); a missing dedup key is a FINDING, not a silent partial.
- **LEG B (a corpus-continuity / byte-determinism TRIPWIRE, NOT the gate)** = the 3-section raw sum ($80,985 leg-1 / $75,985 leg-2, re-pinned #303). RETAINED, re-labeled "exemplar aggregate" — the O4 "served_value" label was a misnomer. Fixtures are the PII-safe `(section, mrr)` projection, so they can compute LEG B but NOT LEG A (needs office_phone/vertical → tests synthesize full-column frames).

§6 #2 anti-RC-C keystone: the fetch plan must cover ALL classifier-active sections (`covered_section_names ⊇ classifier active set`, lowercased) or REFUSE LOUDLY before any charge — a partial sum is the founding wound's silent-loss shape. §6 #9: refusal is a FIRST-CLASS outcome (`ParityLegRefused`), a `ParityObservation` is built ONLY on SWAPPED+coverage-clean. §6 #8: only scalars + a PII-safe per-classification digest land in receipts; office_phone never does.

## substrate-v2 arming: src consumes tests/harness (2026-08-03)

`src/autom8_asana/substrate/live.py` + `prov_sweep.py` (WU-3 arming, PR #305) are an **in-repo operator tool**, not deployed code — they intentionally import the parity substrate from `tests.harness.substrate_gate` (Materialization, PacedLiveParitySource, PerDayBudgetLedger, get_process_fetcher). Kept OUT of `substrate/__init__.py` (never a deployed import). Two gotchas this required:
1. mypy: added `[[tool.mypy.overrides]] module = "tests.harness.substrate_gate.*" follow_imports = "silent"` in pyproject — src is strict-checked against real harness types but the harness's own pre-existing errors (e.g. `cases.HarnessRefusePayload` SunsetBreach variance) are suppressed. Without it, `mypy src/` surfaces a harness error as if new.
2. `test_serve_raw_read_privacy.py` [H17] allowlist: live/prov_sweep were added to `_ALLOWED_STORE_IMPORTERS` (they import the store TYPE to wire rebuild/observe) but NOT to `_ALLOWED_READ_CURRENT_CALLERS` — the F-2 reachability tooth still bites if they ever call `.read_current`.

Also: `AsanaError` is NOT an `Autom8Error`, so feeding a raw 429 to `core.retry`'s classifier `AttributeError`s on `error.response.get(...)` (response is httpx/None, not a botocore dict). Wrap boundary exceptions in `parity.ParityOutboundError` before the RetryOrchestrator (parity.py already documents this).
