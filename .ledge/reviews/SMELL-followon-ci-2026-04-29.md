---
type: review
status: draft
---

# SMELL Follow-on CI Failures — 2026-04-29

## Run anchor

**Primary evidence anchor (per dispatch)**: `https://github.com/autom8y/autom8y-asana/actions/runs/25109444280`
- Run ID: `25109444280`
- Triggering event: `pull_request` against PR #41 merge
- Head SHA at run time: `c1faac00b937f552303538cf4ca0adc04ce44833` (the C3 envelope commit itself)
- Created: 2026-04-29T12:42:04Z
- Status at audit time: `in_progress` (optional jobs still pending; the 3 failures of interest are CONCLUDED `failure`)

**Newer main run (post-PR #42 merge)**: run ID `25110863564`, head SHA `e27cbf2dfa06ccb8a7b21c4bab078b082000ff7c`, created 2026-04-29T13:11:23Z, status `in_progress` at audit time. Cited per drift-audit-discipline; results not yet available so anchor remains the original failure-surfacing run.

**Pre-C3 baseline run (drift-audit anchor)**: run ID `25107886214`, head SHA `848525b9` (PR #40 merge, immediately before PR #41), 2026-04-29T12:07:09Z. Used to bound which failures pre-existed C3 vs. were introduced by C3.

**Last known-green run**: run ID `25056961653`, head SHA `3d06ed12`, 2026-04-28T13:53:04Z. All four test shards green, OpenAPI Spec Drift green, Lint & Type Check green. Bounds the introduction window for F2/F3.

**openapi.json on disk at audit time (sha c1faac00)**: present at `docs/api-reference/openapi.json` (319 KB), generator at `scripts/generate_openapi.py` (2.4 KB). Both verified via filesystem inspection.

## F1 — Lint & Type Check / Run linting

- **Workflow-run anchor**: `https://github.com/autom8y/autom8y-asana/actions/runs/25109444280/job/73579200300`
  - Job ID: `73579200300` ("ci / Lint & Type Check")
  - Step: `Run linting` (step 13; the step `Check formatting` at step 12 ran green — distinct from C1 prior fix scope)
  - Command (verbatim, log line 484): `uv run --no-sources ruff check .`
  - Failure log line range: 502 (first I001) through 1005 (`Found 27 errors.`) → 1010 (`##[error]Process completed with exit code 1.`)

- **Failure signature (verbatim, ≤5 lines)**:
  ```
  I001 [*] Import block is un-sorted or un-formatted
    --> src/autom8_asana/api/routes/_exports_helpers.py:25:1
  F401 [*] `pydantic.ValidationError` imported but unused
    --> src/autom8_asana/api/routes/exports.py:44:52
  Found 27 errors.
  ```

- **Affected file(s)** (absolute paths, deduplicated from 27 ruff diagnostics):
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/_exports_helpers.py` (lines 25, 29, 109, 144, 147, 168, 171, 349, 376, 401, 421)
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/exports.py` (lines 38, 43, 44, 242, 339, 383, 406, 418)
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/fleet_query.py:29`
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/query.py:17`
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/services/query_service.py:21`
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/api/test_exports_contract.py:12`
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/api/test_exports_handler.py:18`
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/api/test_exports_helpers.py:17`
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/api/test_exports_helpers_walk_predicate_property.py:21`
  - All 9 affected files verified extant on disk.

- **Classification**: `independent-pre-existing`

- **Evidence chain**:
  1. Pre-C3 baseline run `25107886214` (sha 848525b9, 2026-04-29T12:07:09Z) job `73573718711` ("ci / Lint & Type Check") was already FAILURE.
  2. Pre-C3 lint failure mode was at `Check formatting` step (`Would reformat: src/autom8_asana/api/routes/_exports_helpers.py`, etc. — pre-c1faac00 log lines 466-472). Ruff jobs short-circuit on first non-zero step: format-check failed → lint-check never executed.
  3. PR #41 commit `3eeff7a8 style: apply ruff format to restore Lint & Type Check CI gate` resolved the format-check step.
  4. With format-check now green at run `25109444280`, the next step `Run linting` (`ruff check .`) ran for the first time and surfaced 27 pre-existing I001 (un-sorted imports) and F401 (unused imports) violations.
  5. The cited file:line list above includes both src and test files with imports of `from autom8_asana.api.routes.exports import (…)`. The complaint is about IMPORT ORDER inside those files, not about the SHAPE of what is being imported — no `data`/`meta` symbol nor 200-response-schema reference appears in any of the 27 diagnostics. Therefore F1 is unrelated to the C3 envelope wrap.
  6. Distinction from prior engagement's C1 honored: C1 fixed step 12 `Check formatting`; F1 fires at step 13 `Run linting` — different ruff sub-command (`format --check` vs `check`), different rule set, different log evidence.

## F2 — OpenAPI Spec Drift

- **Workflow-run anchor**: `https://github.com/autom8y/autom8y-asana/actions/runs/25109444280/job/73579200333`
  - Job ID: `73579200333` ("ci / OpenAPI Spec Drift")
  - Step: `Check OpenAPI spec drift`
  - Command (verbatim, log line 530): `uv run --no-sources python scripts/generate_openapi.py --check`
  - Failure log line range: 558 (`ERROR: OpenAPI spec drift detected.`) through 562 (`##[error]Process completed with exit code 1.`)

- **Failure signature (verbatim, ≤5 lines)**:
  ```
  ERROR: OpenAPI spec drift detected.
    Committed: /home/runner/work/autom8y-asana/autom8y-asana/docs/api-reference/openapi.json
    Generated: /tmp/tmpexkfhwls.json
    Run 'just spec-gen' to regenerate.
  ```

- **Affected file(s)**:
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/docs/api-reference/openapi.json` (committed spec; 319 KB; 9395+ lines). Specifically the two paths edited by C3:
    - `openapi.json:3733-3741` (`/api/v1/exports` POST 200 response schema)
    - `openapi.json:8353-8361` (`/v1/exports` POST 200 response schema)
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/scripts/generate_openapi.py` (generator that drives `--check`)
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/exports.py` (route handlers `post_export_v1` / `post_export_api_v1`; per `git show c1faac00 -- src/autom8_asana/api/routes/exports.py` returned NO output — exports.py was NOT modified by C3)

- **Classification**: `C3-consumer-follow-on`

- **Evidence chain**:
  1. Pre-C3 baseline run `25107886214` (sha 848525b9): job "ci / OpenAPI Spec Drift" status = SUCCESS. The drift did not exist pre-C3.
  2. C3 commit `c1faac00b937f552303538cf4ca0adc04ce44833` ("refactor(api): wrap exports.post 200 responses in {data, meta} envelope for fleet conformance") modified ONLY `docs/api-reference/openapi.json` (per `git show --stat c1faac00`: `1 file changed, 6 insertions(+), 2 deletions(-)`).
  3. C3 commit message states verbatim: "Consumer cross-check: route handlers use response_model=None and return fastapi.Response directly from _format_dataframe_response. The openapi.json change is documentation-only — no Python runtime behavior changes."
  4. The committed `openapi.json:3736-3740` now contains `"$ref": "#/components/schemas/SuccessResponse"` (envelope shape) — verified by current-file read at audit time.
  5. The CI step regenerates spec from FastAPI sources via `scripts/generate_openapi.py --check`, which introspects the route handlers in `src/autom8_asana/api/routes/exports.py`. Because those handlers still declare `response_model=None` (unchanged by C3), the generator emits `schema: {}` for the 200 response (the pre-C3 shape).
  6. Result: committed-spec ≠ generated-spec at exactly the two locations C3 hand-edited (`openapi.json:3736` and `openapi.json:8356`). The drift is the structural consequence of editing the spec-output without editing the spec-source-of-truth (the FastAPI handler return-type annotation).
  7. Cross-stream concurrence: log error message names `Committed: docs/api-reference/openapi.json`; `git show c1faac00` shows `docs/api-reference/openapi.json` was the sole file modified; commit message acknowledges `response_model=None` was retained. All three streams (CI log + git tree + commit prose) converge on the same artifact.

## F3 — Test shard 1/4

- **Workflow-run anchor**: `https://github.com/autom8y/autom8y-asana/actions/runs/25109444280/job/73579221418`
  - Job ID: `73579221418` ("ci / Test (shard 1/4)")
  - Step: `Run tests with coverage`
  - Failure log line range: 7316-7336 (test stack frame) and short-summary at log line 17564 (`FAILED tests/validation/persistence/test_performance.py::TestEndToEndPerformance::test_session_track_100_entities`); job exit at log line 17567 (`##[error]Process completed with exit code 1.`)
  - Headline outcome (log line 17565): `===== 1 failed, 3339 passed, 4 skipped, 124 warnings in 316.32s (0:05:16) ======`

- **Failure signature (verbatim, ≤5 lines)**:
  ```
  >       assert elapsed_ms < HARD_TRACKING_100_ENTITIES_MS * 2  # Allow overhead
  E       assert 1091.6969589999894 < (200 * 2)
  tests/validation/persistence/test_performance.py:366: AssertionError
  FAILED tests/validation/persistence/test_performance.py::TestEndToEndPerformance::test_session_track_100_entities - assert 1091.6969589999894 < (200 * 2)
  ```

- **Affected file(s)**:
  - `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/validation/persistence/test_performance.py:355-366` (test body) and `:41` (constant `HARD_TRACKING_100_ENTITIES_MS = 200`)
  - Subject under test: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/persistence/` (SaveSession.track loop over 100 in-memory `Task` objects)

- **Classification**: `independent-pre-existing` (specifically: wall-clock performance assertion on CI runner; flake-class)

- **Evidence chain**:
  1. Last-known-green run `25056961653` (sha 3d06ed12, 2026-04-28T13:53:04Z): all 4 test shards SUCCESS — including shard 1/4. F3 did not exist at that commit.
  2. Pre-C3 baseline run `25107886214` (sha 848525b9, 2026-04-29T12:07:09Z): all 4 test shards SUCCESS — including shard 1/4. F3 did not exist immediately before C3 either.
  3. Failure window is bounded between `848525b9` and `c1faac00`. The intervening commits are: `3eeff7a8` (ruff format), `f8b5247d` (semantic baseline + M-05 type strictness), `c1faac00` (the envelope wrap).
  4. `git log --oneline 848525b9..c1faac00 -- tests/validation/persistence/ src/autom8_asana/persistence/` returned NO commits. Neither the failing test file nor the persistence package source was modified in the failure window.
  5. The test body (verified at `tests/validation/persistence/test_performance.py:355-366`):
     ```python
     def test_session_track_100_entities(self) -> None:
         client = create_mock_client()
         tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(100)]
         start = time.perf_counter()
         with SaveSession(client) as session:
             for task in tasks:
                 session.track(task)
         elapsed_ms = (time.perf_counter() - start) * 1000
         assert elapsed_ms < HARD_TRACKING_100_ENTITIES_MS * 2  # Allow overhead
     ```
     The assertion is wall-clock ms < 400 (HARD_TRACKING_100_ENTITIES_MS=200, doubled). Observed 1091.7ms.
  6. The test invokes `SaveSession.track()` over an in-memory `mock_client`. It does NOT make any HTTP call to `/exports` nor decode any 200 response body. There is no syntactic or semantic touch point between this test and the C3 envelope shape change.
  7. Same-shard sibling test `TestDependencyGraphOverhead::test_sorting_100_entities_chain_timing` (same file, also wall-clock-asserting) passed at log line 6630. The failure is localized to one wall-clock assertion, consistent with CI runner performance variance rather than a content regression.
  8. Cross-stream concurrence: pytest short-summary names the test verbatim; git history shows zero source/test churn in the relevant package within the failure window; assertion error message numerically pins observed (1091.7) and threshold (400).

## Diagnostic summary

Three failures, three classifications: F1 = `independent-pre-existing` (un-sorted-imports + unused-imports unmasked when prior engagement's C1 ruff-format fix cleared the upstream `Check formatting` short-circuit, exposing the next-in-pipeline `Run linting` step which had been failing latently); F2 = `C3-consumer-follow-on` (C3 hand-edited `openapi.json` to add `$ref: SuccessResponse` envelope shape but did not modify the FastAPI source-of-truth `response_model=None` in `exports.py`, so `scripts/generate_openapi.py --check` regenerates the pre-C3 `schema: {}` and reports drift against the committed file); F3 = `independent-pre-existing` (wall-clock performance assertion on `SaveSession.track` over 100 in-memory entities asserts `<400ms` but observed 1091.7ms; zero commits to the failing test file or persistence package within the failure window between last-green sha 3d06ed12 and the failing run, and zero syntactic touch points to the `/exports` envelope shape — flake-class). Counts: 2× independent-pre-existing, 1× C3-consumer-follow-on. The dispatch hypothesis ("F2 and F3 are likely C3-consumer follow-on; F1 may be independent") was tested: F2 confirmed, F1 confirmed independent, F3 falsified — F3 is independent flake unrelated to C3. Drift-audit-discipline anchor preserved: every classification rests on a workflow-run-URL + job-ID + step + log-line range + git-history evidence triangulation; no claim relies on stale local impressions. No dispositions issued; recommendations are out of scope per Phase 1 authority boundary and route to architect-enforcer.
