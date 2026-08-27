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

## Worktree testing trap: editable install resolves to the MAIN tree (2026-08-13)

The venv's editable install is a plain `.pth` (`.venv/lib/python3.12/site-packages/_editable_impl_autom8y_asana.pth`) that puts the **main working tree's** `src/` on `sys.path`. So `python -m pytest` run from a `.knossos/worktrees/<name>` worktree silently imports `autom8_asana` from the MAIN tree, NOT the worktree — your edits appear to have no effect (a two-sided RED will stay RED after the fix). Fix: `export PYTHONPATH="$PWD/src"` (PYTHONPATH is prepended before site-packages `.pth` entries; it's a path-based `.pth`, not a PEP-660 import hook, so PYTHONPATH wins). Verify with `python -c "import autom8_asana.query.temporal as t; print(t.__file__)"`. mypy: `export MYPYPATH="$PWD/src"` similarly, and passing worktree file paths explicitly makes it resolve the worktree (confirmable because it can see worktree-only new symbols). No `pythonpath` in pyproject `[tool.pytest.ini_options]`, so nothing overrides this for you.

## OfferTimelineEntry imputation discriminator (EX-3, 2026-08-13)

`SectionTimeline.story_count == 0` is the exact imputed-vs-observed discriminator (reset to 0 in the impute branch at `section_timeline_service.py:363`; genuine timelines carry `len(stories) > 0`). EX-3 surfaced it on the wire: added required `story_count: int` + a `@computed_field imputed: bool` (= `story_count == 0`) to `OfferTimelineEntry`, and an `ImputationSummary` (INFERRED rate) branched on by `summarize_imputation()` in `api/routes/section_timelines.py`, wired into the `SectionTimelinesResponse` envelope. Gotcha: a Pydantic v2 `@computed_field` appears in `model_dump()`/`model_dump_json()` and the **serialization-mode** JSON schema (what FastAPI uses for response docs), but NOT in default validation-mode `model_json_schema()` — so `model_json_schema()` won't show `imputed`; check `model_json_schema(mode="serialization")` or the actual HTTP response. `TemporalFilter._interval_matches` also guards on `timeline.story_count == 0 and self._has_any_criterion()` — an imputed interval is not a transition, so any non-empty filter rejects it (empty filter still matches). This is the correct fix, NOT the `moved_from` workaround, which engages the `idx == 0` guard and drops every offer's genuine first move.

## Pointers

- [Harness guards on scratch git work](harness_guards_scratch_git.md) — `.knossos` substring blocks `rm` anywhere in the command; scratch-clone commits are still conventional-commit validated
- [autom8y monorepo service build env](autom8y-monorepo-service-build-env.md) — worktree `uv sync` works; the main checkout's `.venv` is stale/broken; root ruff excludes ALL test files and `BLE001` noqa is dead there
- [autom8y monorepo test-env traps](autom8y-monorepo-test-env-traps.md) — `VIRTUAL_ENV`/`LOG_LEVEL` leak into worktree runs and silently bind the wrong venv; use `env -u VIRTUAL_ENV -u LOG_LEVEL uv run --frozen` and verify `module.__file__`
- [autom8y CI shellcheck/apt flake](autom8y-ci-shellcheck-apt-flake.md) — a red autom8y gate whose log ends at `Install shellcheck` is infra, not your diff; corroborate via concurrent runs on other branches, then rerun
- [Calendly wire shape + forensic gap](calendly-wire-shape-and-forensic-gap.md) — the OpenAPI spec is credential-free and authoritative (`position` is an INT); rejected webhook BODIES are unrecoverable — only the shape survives, via pydantic's error echo
- [calendly-intake alarm surface is generic 5xx only](calendly-intake-alarm-surface-is-generic-5xx-only.md) — moving a death between pipeline stages buys diagnosis, NOT visibility; every stage-FAILED is the same 500, the discriminating counters are dark, and webhook-recon CRITICAL drift alarms on nothing
- [Calendly org subscription is DISABLED](calendly-org-subscription-disabled-blocks-s04.md) — 2026-08-20: governed ingress delivers nothing (Calendly retry-exhausted it); W5-3 non-fire means no traffic, not health; probe live before planning S-04
- [Staleness guards must be now-relative](staleness-guards-must-be-now-relative.md) — a guard pinned to a fixed calendar instant stays green forever on an expired window; assert vs `now()`, and DISCOVER corpora rather than enumerating named files
- [SDK publish: two-gate MAJOR deadlock + the deploy RACE](autom8y-sdk-publish-two-gate-major-deadlock.md) — off a 0.x ceiling, version-enforcement demands >=1.0.0 but D3.1 refuses any unpublished MAJOR; ALSO sdk-publish and service-deploy fire concurrently on one PR, so "add one SDK method" costs 2 sequenced merges — prefer a service-local typed surface over the shared transport
- [401 precedes routing — no credential-free liveness probe](autom8y-401-precedes-routing-no-liveness-probe.md) — unauthenticated probes 401 on real AND fake paths; prove a deploy via the ECS/Lambda image tag (= short merge sha) and label HTTP liveness UV-P
- [calendly-intake phone fixture 555 trap](calendly-intake-phone-fixture-555-trap.md) — `+1555555xxxx` is INVALID and silently drops to None; use 555-01xx inside a real area code or no-phone tests pass for the wrong reason
- [`[hotfix]` marker greps commit bodies](autom8y-hotfix-marker-greps-commit-messages.md) — writing "no [hotfix] tag" in a commit message SETS the marker; label-only (no bypass) but it falsifies the publish audit trail
- [Read the SERVED commit, not the worktree](autom8y-read-the-served-commit-not-the-worktree.md) — autom8y local HEAD is routinely NOT an ancestor of the deployed sha; resolve it from the Lambda image tag and `git archive` it out
- [autom8y S2S token probe recipe](autom8y-s2s-token-probe-recipe.md) — `sa_*` ids use TEB + Basic auth (not /oauth/token); token is at `data.access_token`; Secrets Manager needs the FULL ARN
- [CascadeNotReady hides behind ASANA_UNAVAILABLE](asana-cascade-not-ready-hides-behind-asana-unavailable.md) — a 503 on asana intake-resolve is often a >20%-null cascade column; the real diagnostic is log-only, and UNAVAILABLE must never be read as ABSENT
- [Scratchpad is shared — assert identity at point of use](scratchpad-is-shared-assert-identity-at-point-of-use.md) — a file you wrote days ago may hold another lane's entity; re-fetch in-turn, name files by uuid, and `assert` identity before any live act
- [Contact cascade gate can never clear](cascade-gate-denominator-vs-orphan-contacts.md) — RESOLVED 2026-08-22 by the rescope below; kept for the diagnosis (it is a denominator question, never a threshold one)
- [Cascade gate denominator rescope](cascade-gate-denominator-rescope.md) — denominator is `parent_gid` not-null, in-frame + no join; business is ROOT and un-gated (read the schema's `cascade:` sources, never an entity list); collapse RAISES; live orphan/joinable fields land on `cascade_key_null_audit`
- [S2S probe via an existing sa_* identity](autom8y-s2s-probe-via-existing-sa-identity.md) — the ECS task's own `SERVICE_CLIENT_ID=asana` can NEVER mint (prefix dispatch needs `client_`/`sa_`); borrow the insights-export lambda's `sa_*` + TEB Basic auth
- [Two DISJOINT required-check lists](autom8y-two-disjoint-required-check-lists.md) — rulesets API and classic branch protection both enforce, with non-overlapping contexts; `CI Summary` is only in the classic one and is usually what blocks
- [EBI witness-ledger re-ratification](ebi-witness-ledger-ratification-blocks-all-merges.md) — RESOLVED; the worked example of answering a census drift-guard by ratification (spec lives in the script; tier must be grounded in `_tier_observed`; never rewrite the generated run receipt)
- [Lambda deploy APPLIES the service terraform](autom8y-lambda-deploy-applies-service-terraform.md) — a `terraform/services/<svc>` change ships on merge (not only via the human-gated Service Terraform); and "served" is the live ALIAS version after the CodeDeploy shift, never `Code.ImageUri`
- [A new EventBridge detail_type publishes NOTHING](autom8y-events-new-detail-type-publishes-nothing.md) — strict mode returns False without raising and never calls PutEvents; MockPublisher documents that it cannot catch this, so bind the return value and verify via TriggeredRules
- [WS-D deadman is blind to future-dated bookings](calendly-intake-deadman-blind-to-future-bookings.md) — the recon scan is a `start_time` band, so `bookings_incomplete` read 0.0 through a live 12-retry loss event
- [EBI metrics are dark + live-probe traps](ebi-metrics-dark-and-live-probe-traps.md) — no prometheus exporter in EBI so any Counter is dark (emit structlog instead); and `datetime().timestamp()` is LOCAL, silently returning zero CloudWatch events
- [calendly-intake logs are ~99% canary](calendly-intake-canary-dominates-traffic.md) — 4321 canary vs 48 organic per 30d; `@requestId` is empty so split by parsed `trace_id`; `notify_complete` drops its `events_published` field on the wire
- [Mutation-prove the LANDING seam, not just your edit](mutation-prove-the-landing-seam-not-just-the-edit.md) — a test that re-implements the branch it claims to exercise passes against any mutant; the cure's landing point is often a file your diff never touched
- [terraform validate is CI-only, and PR checks take ~15min to register](autom8y-terraform-validate-is-ci-only.md) — `terraform fmt` catches nothing semantic; a 1211-char `alarm_description` (cap 1024) cost a full round trip. Encode cheap provider constraints as pytest over the .tf text
- [`intake.business.created` is branch-starved](intake-business-created-is-branch-starved.md) — the producer EXISTS and is wired; one `if ctx.is_new_business` gates it and the CREATE branch has never been taken, so both "write the producer" and "resurrect the SFN" are wrong fixes
- [appointments.start_datetime is a MIXED plane](or4-mixed-datetime-plane-in-appointments.md) — Z/+HH:MM/bare/`'Invalid date'` in one VARCHAR (byte-equality = 0.000% reachable); bare is NEVER UTC; curing the join surfaces a SECOND unearned stamp — rule multi-match on IDENTITY not row count
- [Replay the cure on real data before shipping it](replay-the-cure-on-real-data-before-shipping.md) — synthetic teeth proved the join and were blind to a 28.98% AMBIGUOUS blowout; a read-only replay importing the module's OWN helpers is cheap and catches the swapped-failure-mode class
- [autom8y-data worktree test env](autom8y-data-worktree-test-env.md) — worktree `uv sync` dies on CodeArtifact 401; borrow the MAIN `.venv` + `PYTHONPATH="$PWD/src"`; `-p no:randomly` breaks addopts; `wt.10x-dev.*` fails the name grammar
