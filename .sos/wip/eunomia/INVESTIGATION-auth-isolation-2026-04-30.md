---
type: triage
artifact_type: investigation
rite: eunomia
session_id: session-20260430-001257-0f7223d6
task: EUN-V2-001-A
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2
authored_by: rationalization-executor
evidence_grade: STRONG
adjudication: TEST-SURFACE-CONFIRMED
---

# INVESTIGATION — Auth-Isolation Regression (EUN-V2-001-A)

## §1 Purpose

This artifact discharges EUN-V2-001-A per v2 charter §5.1 reproduce-first protocol.
It documents the local reproduction of the failing test, traces the fixture dependency
chain, confirms or refutes the supplement §6.4 hypothesis, and adjudicates the root
cause location (test surface vs production code). The output of this investigation is
the input to V2-001-B fix-design.

## §2 Reproduction Result

**Status: REPRODUCED LOCALLY. Exit code: 1.**

Command executed:
```bash
pytest -n 4 --dist=load \
  tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503 \
  --tb=short -v
```

Assertion fired verbatim:
```
FAILED tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503
  assert 401 == 503
   +  where 401 = <Response [401 Unauthorized]>.status_code
```

Worker assignment: `[gw0]` — single-item test, assigned to first available worker.
pytest-internal time: 2.49s (local, 1-test isolation run).

**Repro confidence: HIGH.** The assertion is identical to CI (supplement §7.1,
`tests/unit/api/test_routes_resolver.py:463`). Reproduction is NOT environment-specific
to CI; it reproduces identically on macOS-26.4-arm64, Python 3.12.12,
pytest-9.0.2, pytest-xdist 3.8.0.

**Environment fingerprint:**
- Platform: macOS-26.4-arm64-arm-64bit
- Python: 3.12.12
- pytest: 9.0.2
- pytest-xdist: 3.8.0
- autom8y-auth: 3.3.0 (plugin)

**Key observation from reproduction output** (captured stdout call):
```
{"stdlib_logger": "autom8y_auth.middleware", ...
"event": "Auth failed: AUTH-TEB-003 - Token is malformed: Invalid header string:
'utf-8' codec can't decode byte 0x85 in position 0: invalid start byte", ...}
HTTP Request: POST http://testserver/v1/resolve/unit "HTTP/1.1 401 Unauthorized"
```
This is the `JWTAuthMiddleware` rejecting the fake JWT before the FastAPI dependency
layer runs — at `autom8y_auth/middleware.py:223-234`.

**Contrast with CI:** CI had AUTOM8Y_ENV=test (not LOCAL). Locally when run
under `--dist=load`, AUTOM8Y_ENV is also `test` by default (not set). Both
environments fail identically — this is NOT a CI-only issue. The prior
"local passes" observation in supplement §6.4 / HANDOFF notes:47 referred to
the full-suite run, not the isolated test. The isolated test fails locally too.

## §3 Fixture Chain Trace

The failing method signature:

```
class TestResolveDiscoveryIncomplete:           # test_routes_resolver.py:415
    def test_discovery_incomplete_returns_503(self) -> None:   # :418
```

**Critical: this test takes NO pytest fixture arguments.** It receives only
`self`. It does NOT consume `client`, `app`, `reset_singletons`, or any
other conftest fixture.

Fixture resolution chain for this test under `--dist=load`:

```
test_discovery_incomplete_returns_503(self)
  └── autouse fixtures only:
      ├── reset_all_singletons (tests/conftest.py:193, function-scope, autouse)
      │     calls SystemContext.reset_all()  # clears EntityProjectRegistry + all singletons
      │
      └── reset_singletons (tests/unit/api/conftest.py:115, function-scope, autouse)
            calls: clear_bot_pat_cache()
                   reset_auth_client()          # sets _auth_client = None
                   _populate_test_registry()    # ← populates EntityProjectRegistry
```

The test then MANUALLY constructs its own `test_app` (line 433):
```python
EntityProjectRegistry.reset()                           # :421
# ... patches _discover_entity_projects to no_setup ...
test_app = create_app()                                 # :433
test_app.dependency_overrides[get_auth_context] = _mock_get_auth_context  # :444
```

The `dependency_overrides` override is applied AFTER `create_app()` is called.
`create_app()` instantiates `JWTAuthMiddleware` at the ASGI middleware layer.

```
test_app = create_app()
  └── create_fleet_app(...)
      └── add_middleware(JWTAuthMiddleware, config=jwt_auth_config)
          └── JWTAuthMiddleware.__init__ reads os.environ for AuthSettings()
              AUTOM8Y_ENV=test → dev_mode=False by default
```

When the test then makes:
```python
with TestClient(test_app) as test_client:
    response = test_client.post("/v1/resolve/unit",
        headers={"Authorization": f"Bearer {jwt_token}"},  # "header.payload.signature"
```

Request processing order:
1. `JWTAuthMiddleware.dispatch()` — middleware layer fires FIRST (ASGI layer)
2. Token `"header.payload.signature"` → AUTH-TEB-003 malformed token → returns 401
3. FastAPI dependency injection NEVER runs — including `dependency_overrides[get_auth_context]`

The `dependency_overrides` override never executes because the middleware
returns 401 before the route handler's dependency graph resolves.

## §4 Auth State Setup Analysis

**What the test intends:** The `_mock_get_auth_context` override (line 437-443)
would bypass real JWT validation and supply a stub `AuthContext` if the
FastAPI dependency layer were reached. This is the correct pattern for
suppressing dependency-level auth checks.

**What actually happens:** The `JWTAuthMiddleware` runs at ASGI middleware
altitude — before FastAPI dispatches to any route or resolves any dependency.
`dependency_overrides` only applies within the FastAPI DI system (route
handler layer). It has NO effect on ASGI middleware.

**Scope analysis:**

| Component | Scope | Worker-Local? | Role |
|---|---|---|---|
| `reset_all_singletons` (root conftest:193) | function, autouse | Yes (T1A) | Clears singletons |
| `reset_singletons` (api conftest:115) | function, autouse | Yes | Clears auth cache + populates registry |
| `JWTAuthMiddleware` (inside `test_app`) | process-global at middleware altitude | N/A | Rejects non-dev-mode tokens |
| `dependency_overrides[get_auth_context]` | FastAPI DI layer (never reached) | N/A | Would bypass auth IF reached |

**The module-scoped `app` fixture** (api conftest:50-105) correctly handles
this by setting `AUTH__DEV_MODE=true` and `AUTOM8Y_ENV=LOCAL` in `os.environ`
BEFORE calling `create_app()`. This puts `JWTAuthMiddleware` into dev-mode
bypass. The `test_discovery_incomplete_returns_503` test does NOT use the
module-scoped `app` fixture — it creates its own `test_app` via `create_app()`
WITHOUT setting these environment variables.

**Worker-isolation note:** The supplement §6.4 hypothesis about worker
co-location under `--dist=loadfile` vs `--dist=load` is partially correct
in effect (the test fails under both when run in isolation), but the
co-location mechanism described is imprecise. The actual co-location
benefit under `--dist=loadfile` would be:

Under `--dist=loadfile`, `test_routes_resolver.py` tests are grouped on
the SAME worker as all other resolver tests. The `app` fixture (module-scoped)
from that same file runs on the same worker and sets `AUTH__DEV_MODE=true`
in `os.environ`. That environment variable persists in the worker process
for the duration of the module. When `test_discovery_incomplete_returns_503`
runs next (same worker, same process), `os.environ["AUTH__DEV_MODE"]` is
still `"true"` from the module-scoped fixture setup phase. The
`create_app()` call inside the test sees `AUTH__DEV_MODE=true` and builds
`JWTAuthMiddleware` in dev-mode bypass.

Under `--dist=load`, `test_discovery_incomplete_returns_503` can land on a
DIFFERENT worker that has NOT yet run the module-scoped `app` fixture (or
on a worker where `os.environ["AUTH__DEV_MODE"]` was not set). The env var
is absent, `dev_mode=False`, and the middleware rejects the fake token.

This is confirmed by the reproduction output showing `autom8y_env: TEST` (not LOCAL)
and `dev_mode: False` in the `auth_client_initialized` log at captured stdout call.

## §5 Hypothesis Confirmation

**Supplement §6.4 hypothesis** (verbatim):
> T1A's worker-local `_reset_registry` refactor + T1D's `--dist=load` switch interact
> with `routes/resolver.py` auth dependency. `--dist=loadfile` masked the issue by
> co-locating auth-fixture and resolver tests on the same xdist worker. Under `--dist=load`,
> they distribute, leaving the resolver-test worker un-seeded.

**Confirmed with precision refinement.** The hypothesis is directionally correct:
`--dist=loadfile` masked the issue by co-location; `--dist=load` distributes and
exposes it. However, the mechanism is OS-environment state propagation, not
registry seeding:

- **NOT about**: `EntityProjectRegistry` seeding (the test intentionally resets
  it via `EntityProjectRegistry.reset()` at line 421; registry state is
  irrelevant to the 401 failure).
- **IS about**: `os.environ["AUTH__DEV_MODE"]` set by the module-scoped `app`
  fixture (api conftest:66-68) persisting in the worker process, and
  `test_discovery_incomplete_returns_503` incorrectly depending on that
  ambient env-var state when it calls `create_app()` at line 433.

The T1A worker-local `_reset_registry` refactor at `system_context.py:33`
(commit `367badba`) is NOT the direct cause of the 401. T1A is causally
upstream in the following sense: T1A enabled `--dist=load` safety for
the `SystemContext.reset_all()` autouse pattern, which is what motivated
T1D's `--dist=load` switch. The `--dist=load` switch (T1D, commit `8f99a801`)
is the proximate cause of distributing the test to a worker where
`AUTH__DEV_MODE` is not set.

## §6 Adjudication

**TEST-SURFACE-CONFIRMED.**

Root cause is entirely within the test surface. The production code
(`routes/resolver.py`, `api/main.py`, `autom8y_auth/middleware.py`) is
functioning correctly: the middleware is correctly rejecting an invalid token
in a non-dev environment. The test incorrectly relies on ambient
`os.environ["AUTH__DEV_MODE"]` state that was set by a module-scoped fixture
in the same test file, which is only present when the file's other tests ran
on the same worker first.

**Why this is NOT a production-code issue:** The production `create_app()`
correctly reads `AUTH__DEV_MODE` from the environment. The bug is that
`test_discovery_incomplete_returns_503` calls `create_app()` without
first establishing the environment invariants that the test requires.
The fix is in the test, not in any src file.

**T1A exoneration:** `system_context.py:28` (commit `367badba`) did not
introduce any new global-state coupling. The worker-local registry is
irrelevant to the 401 failure path. T1A is not a contributing cause.

**Risk class: LOW.** The fix is additive-only to the test method. It does
not modify the module-scoped `app` fixture, the `reset_singletons` autouse,
or any production code. The SCAR cluster is unaffected.

## §7 Recommended Next Action

**V2-001-B fix target: `tests/unit/api/test_routes_resolver.py:418-465`**
Class `TestResolveDiscoveryIncomplete`, method `test_discovery_incomplete_returns_503`.

**Fix shape (1-3 sentences):**
The test must set `AUTH__DEV_MODE=true` and `AUTOM8Y_ENV=LOCAL` in `os.environ`
before calling `create_app()` at line 433, and restore them after (matching
the pattern in `tests/unit/api/conftest.py:64-105` `app` fixture). The simplest
form is adding an `os.environ` context or `monkeypatch.setenv` call around the
`create_app()` call, or extracting a helper that mirrors the env-setup performed
by the module-scoped `app` fixture. This makes the test self-contained and
independent of worker execution order.

**Approximate patch (illustrative):**
```python
# At test_routes_resolver.py:430, before create_app():
import os
_prev_dev = os.environ.get("AUTH__DEV_MODE")
_prev_env = os.environ.get("AUTOM8Y_ENV")
os.environ["AUTH__DEV_MODE"] = "true"
os.environ["AUTOM8Y_ENV"] = "LOCAL"
try:
    test_app = create_app()
    ...
    # existing test body unchanged
    ...
finally:
    if _prev_dev is None:
        os.environ.pop("AUTH__DEV_MODE", None)
    else:
        os.environ["AUTH__DEV_MODE"] = _prev_dev
    if _prev_env is None:
        os.environ.pop("AUTOM8Y_ENV", None)
    else:
        os.environ["AUTOM8Y_ENV"] = _prev_env
```

Alternatively, since `reset_auth_client()` is called by `reset_singletons`
autouse (api conftest:124), the auth client will be re-initialized fresh on
this worker — so the env vars need only be set around `create_app()`, not
around the `validate_service_token` call. The `dependency_overrides` pattern
already in the test is correct for the FastAPI DI layer; the only missing
piece is the middleware bypass.

**Risk class: LOW.** No production code modification. No changes to conftest
fixtures. No changes to module-scoped `app` fixture. Additive-only to one
test method.

## §8 Open Questions / Risks

**OQ-1: Why did the prior "local passes" observation differ?**
Supplement notes (HANDOFF §notes:47-49) state "Local pytest -n 4 --dist=load
PASSED (12,918 tests; verified during executor run)". This was a full-suite run
where the module-scoped `app` fixture ran on the same worker (under loadfile
ordering which had not yet been changed to load) or under load topology where
the module's other tests happened to land on the same worker first. The test
was not isolated; in the full suite the race condition is probabilistic. With
a 4-worker pool and multiple test files, sometimes the `app` fixture co-locates;
sometimes it does not — explaining why the full-suite run passed locally while
CI (potentially different worker startup ordering or env-var state) failed.

**OQ-2: Is there analogous pattern in other test files?**
The `TestResolveDiscoveryIncomplete` pattern — creating a fresh `create_app()`
inside a test without setting env vars — may exist in other test files. A
grep for `create_app()` inside test methods (as opposed to fixtures) would
confirm scope. This investigation is bounded to the single failing test per
charter §8.4, but V2-001-B executor should note this as a potential
follow-on hygiene item.

**OQ-3: The `reset_auth_client()` in `reset_singletons` autouse.**
`reset_auth_client()` nulls `_auth_client` (jwt_validator.py:97-109). This
means the auth client is re-initialized lazily on next call, reading env vars
at that time. If `AUTH__DEV_MODE` is not in env at re-initialization time
(which it is not, absent the fix), the new client has `dev_mode=False`. This
is consistent with the reproduction: the `auth_client_initialized` log shows
`autom8y_env: TEST, dev_mode: False`. The fix must establish the env vars
before `create_app()` initializes the `JWTAuthMiddleware` config (which reads
env at construction time), not before the auth client is initialized (which
is lazy). Both must be covered.

**OQ-4: Charter §8.4 authority boundary preserved.**
`routes/resolver.py`, `api/main.py`, `auth/jwt_validator.py`,
`autom8y_auth/middleware.py` — all READ ONLY per this investigation. No
modifications made or recommended to any src file. Fix is exclusively in
`tests/unit/api/test_routes_resolver.py`.

---

END INVESTIGATION-auth-isolation-2026-04-30.
Adjudication: TEST-SURFACE-CONFIRMED.
Fix target: `tests/unit/api/test_routes_resolver.py:418-465`.
Risk class: LOW.
V2-001-B unblocked.
