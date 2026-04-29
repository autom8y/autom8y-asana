---
type: spec
spec_subtype: tdd
id: TDD-lambda-default-bucket-refactor
status: proposed
date: "2026-04-20"
rite: hygiene
initiative: "Ecosystem env/secret platformization alignment"
res_id: RES-002
links_to:
  - ADR-bucket-naming  # ADR-0002 — canonical bucket name
  - TDD-cli-preflight-contract  # CFG-006 preflight pattern (handler-side equivalent rejected — see Chosen Option)
source_handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
authored_by: architect-enforcer (hygiene rite, sprint-D Wave 0)
evidence_grade: strong
---

# TDD — Lambda `DEFAULT_BUCKET` refactor (RES-002)

## Scope

- **In scope**: Three call sites that hardcode `"autom8-s3"` as a fallback:
  1. `src/autom8_asana/lambda_handlers/checkpoint.py:29` (`DEFAULT_BUCKET` module constant)
  2. `src/autom8_asana/lambda_handlers/checkpoint.py:38` (`_default_bucket()` fallback `or DEFAULT_BUCKET`)
  3. `src/autom8_asana/lambda_handlers/cache_warmer.py:273` (`or "autom8-s3"` fallback expression)
- **In scope (adjacent)**: `src/autom8_asana/settings.py:348` — `S3Settings.bucket: str = Field(default="", ...)` changes to `Field(default="autom8-s3", ...)`.
- **In scope (docstring hygiene)**: `checkpoint.py:11` (module docstring env-var line), `checkpoint.py:148` (class docstring example). Update to reference `S3Settings` default, not bare string.
- **Out of scope**: `docker-compose.override.yml:33`, `.env/defaults:21`, `/Users/tomtenuta/Code/a8/manifest.yaml:476`. ADR-0002 ratified these as canonical and out of repo edit boundary (manifest is cross-repo).

## Decisive investigation finding

`S3Settings.bucket` currently has `Field(default="", ...)` (empty string), NOT `"autom8-s3"`. The handler fallbacks (`or DEFAULT_BUCKET`, `or "autom8-s3"`) are **load-bearing** when `ASANA_CACHE_S3_BUCKET` is unset. This makes Options A (fail-fast) and B (centralize constant) structurally heavier than Option C; Option C closes the gap at the Settings layer where it semantically belongs.

**ADR-0002 Consequences conflict note**: ADR-0002 (lines 131-132) declares `DEFAULT_BUCKET` constant and the `or "autom8-s3"` expression "no change." RES-002 (sprint-D handoff lines 83-91) explicitly mandates changing them. This TDD resolves the conflict by preserving ADR-0002's **canonical name** (`autom8-s3`) and **behavior** (fallback value still `"autom8-s3"` when env unset) while relocating the string to a single authoritative source (Pydantic default). The ADR's canonical declaration is honored; only the declaration **site** moves from duplicated-handler-constant to single-Settings-default.

## Chosen option: **C — Lean on Pydantic Settings default**

Move `"autom8-s3"` from the two handler call sites into `S3Settings.bucket` as its Pydantic default.

**Rationale (bounded by the three constraints)**:

1. **Behavior preservation**: When env var is unset, `get_settings().s3.bucket` returns `"autom8-s3"` under Option C (via Pydantic default) identically to how the handlers returned `"autom8-s3"` under the current fallback. The `or "autom8-s3"` expression becomes dead code that can be removed without behavior change. When env var IS set (including to empty string via explicit `ASANA_CACHE_S3_BUCKET=""`), Pydantic coerces empty string to the empty-string value (NOT the default — Pydantic fallback-on-unset semantics). This matches the handler `or` expression for non-empty env values but diverges for the `ASANA_CACHE_S3_BUCKET=""` case. See **Rejection criterion 1** below — we accept this divergence because no production deploy config is known to set the var to empty string, and the divergence fails fast (empty bucket name → boto3 error) rather than silent wrong-bucket.
2. **Minimal blast radius**: One line change in `settings.py`, removal of the `or` expression at two handler sites, removal of the `DEFAULT_BUCKET` module constant and `_default_bucket()` helper. No new module, no new dependency direction. Contained within the existing Settings architecture.
3. **ADR-0002 consistency**: ADR-0002 canonizes `"autom8-s3"`. Option C relocates the canonical name into the type-system boundary (`S3Settings`) where it semantically belongs — the Settings class is the documented single source of truth for env-sourced config (see `settings.py:8-64` module docstring and line 789 example). The ADR's canonical declaration is preserved; only its expression site moves.

**Rejection of A (fail-fast)**: Would change deploy-time semantics. A Lambda deploy whose env var is missing would raise at startup under Option A but silently default under status quo. The sprint is hygiene scope, not behavior-change scope. Changing fail-behavior crosses into operational semantics territory and requires SRE consultation, which is not in sprint-D wave 0.

**Rejection of B (centralize constant)**: Still a magic string — just in a different file. Doesn't close the structural smell (duplication + implicit default), only relocates it. Adds a new module (`_defaults.py`) or a new top-level constant in `settings.py` for no semantic gain over C.

**Rejection of D (hybrid)**: Adds a startup assertion + warning for ambiguous benefit. The warning "value equals canonical default" has no actionable meaning when `autom8-s3` IS the canonical default in dev AND in prod (per ADR-0002 and monorepo manifest line 476). Option D's distinguishing value (dev-vs-prod-misconfig) collapses when dev and prod share the canonical name — which they do.

## Before / after snippets

### `src/autom8_asana/settings.py:348`

```diff
-    bucket: str = Field(default="", description="S3 bucket name for cache storage")
+    bucket: str = Field(
+        default="autom8-s3",
+        description="S3 bucket name for cache storage (canonical per ADR-0002)",
+    )
```

### `src/autom8_asana/lambda_handlers/checkpoint.py:11` (module docstring)

```diff
 Environment Variables:
-    ASANA_CACHE_S3_BUCKET: S3 bucket for checkpoint storage (default: autom8-s3)
+    ASANA_CACHE_S3_BUCKET: S3 bucket for checkpoint storage
+        (default resolved via S3Settings; see ADR-0002 for canonical name)
```

### `src/autom8_asana/lambda_handlers/checkpoint.py:28-38`

```diff
-# Default configuration
-DEFAULT_BUCKET = "autom8-s3"
-DEFAULT_PREFIX = "cache-warmer/checkpoints/"
-DEFAULT_STALENESS_HOURS = 1.0
-
-
-def _default_bucket() -> str:
-    """Resolve S3 bucket from settings with fallback to DEFAULT_BUCKET."""
-    from autom8_asana.settings import get_settings
-
-    return get_settings().s3.bucket or DEFAULT_BUCKET
+# Default configuration
+DEFAULT_PREFIX = "cache-warmer/checkpoints/"
+DEFAULT_STALENESS_HOURS = 1.0
+
+
+def _default_bucket() -> str:
+    """Resolve S3 bucket from S3Settings (canonical per ADR-0002)."""
+    from autom8_asana.settings import get_settings
+
+    return get_settings().s3.bucket
```

**Janitor note**: `DEFAULT_BUCKET` is exported and imported by the checkpoint test (see Test-side implications). Do NOT simply delete — the import in the test is load-bearing and must be updated in the same commit.

### `src/autom8_asana/lambda_handlers/checkpoint.py:148` (class docstring)

```diff
     Example:
-        >>> mgr = CheckpointManager(bucket="autom8-s3")
+        >>> mgr = CheckpointManager(bucket="autom8-s3")  # canonical name per ADR-0002
```

Minimal change — docstring example retains the literal because doctests read literally, but adds the ADR cross-reference.

### `src/autom8_asana/lambda_handlers/cache_warmer.py:272-274`

```diff
     checkpoint_mgr = CheckpointManager(
-        bucket=get_settings().s3.bucket or "autom8-s3",
+        bucket=get_settings().s3.bucket,
     )
```

## Behavior-preservation test plan

**Anchor tests (must pass unchanged in behavior; test file updates required per below)**:

| Test | File:line | Exercises | Post-refactor assertion |
|------|-----------|-----------|-------------------------|
| `test_default_bucket_fallback` | `tests/unit/lambda_handlers/test_checkpoint.py:319-323` | `CheckpointManager()` with env cleared falls back to default | Updated to assert `mgr.bucket == "autom8-s3"` (literal) OR assert `mgr.bucket == get_settings().s3.bucket` — **see Test-side implications** |
| `test_default_configuration` | `tests/unit/lambda_handlers/test_checkpoint.py:311-317` | env `ASANA_CACHE_S3_BUCKET=env-bucket` → `mgr.bucket == "env-bucket"` | **Passes unchanged** — env override semantics identical under Option C |
| All other `TestCheckpointManager` tests | `tests/unit/lambda_handlers/test_checkpoint.py:*` | Save/load/clear roundtrips with explicit `bucket="test-bucket"` | **Pass unchanged** — inject explicit bucket, fallback path not exercised |
| `test_cache_warmer.py::*` | `tests/unit/lambda_handlers/test_cache_warmer.py` | No tests assert on `CheckpointManager(bucket=...)` construction argument (grep confirmed zero matches) | **Pass unchanged** — cache_warmer tests mock `CheckpointManager` as a whole, don't inspect bucket |
| `test_main.py::` metrics preflight | `tests/unit/metrics/test_main.py:69` | `monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")` | **Pass unchanged** — sets env explicitly, doesn't depend on default |

**Janitor verification command (run post-refactor, before commit)**:
```
uv run pytest tests/unit/lambda_handlers/test_checkpoint.py tests/unit/lambda_handlers/test_cache_warmer.py tests/unit/test_settings.py tests/unit/metrics/test_main.py -v
```

All tests in these four files MUST pass. If `test_default_bucket_fallback` fails because the test imports `DEFAULT_BUCKET` which no longer exists, janitor updates that test in the same commit (see next section).

## Test-side implications

Three test-file edits required as part of the same refactor commit:

1. **`tests/unit/lambda_handlers/test_checkpoint.py:20-26`** — remove `DEFAULT_BUCKET` from the import list:
   ```diff
   from autom8_asana.lambda_handlers.checkpoint import (
   -    DEFAULT_BUCKET,
       DEFAULT_PREFIX,
       DEFAULT_STALENESS_HOURS,
       CheckpointManager,
       CheckpointRecord,
   )
   ```

2. **`tests/unit/lambda_handlers/test_checkpoint.py:319-323`** — rename test and update assertion:
   ```diff
   -    def test_default_bucket_fallback(self) -> None:
   -        """Manager falls back to DEFAULT_BUCKET when env not set."""
   +    def test_default_bucket_from_settings(self) -> None:
   +        """Manager resolves bucket from S3Settings Pydantic default (ADR-0002) when env not set."""
           with patch.dict("os.environ", {}, clear=True):
   +            from autom8_asana.settings import reset_settings
   +            reset_settings()  # clear singleton so Pydantic re-reads env
               mgr = CheckpointManager()
   -            assert mgr.bucket == DEFAULT_BUCKET
   +            assert mgr.bucket == "autom8-s3"
   ```
   The `reset_settings()` call is load-bearing: `get_settings()` caches a singleton, and prior tests in the same module may have populated it with env values. Clearing `os.environ` does not clear the cached Settings. Without `reset_settings()`, the test passes for the wrong reason (cached value from prior test).

3. **Grep-sweep to confirm no other files import `DEFAULT_BUCKET`**:
   ```
   rg 'from autom8_asana.lambda_handlers.checkpoint import.*DEFAULT_BUCKET'
   rg 'checkpoint\.DEFAULT_BUCKET'
   ```
   Confirmed zero matches outside `test_checkpoint.py:21` at TDD authorship time. If the janitor's grep discovers additional importers, PAUSE and re-route to architect — scope has widened.

**Likely-affected test files: 1** (`test_checkpoint.py`). Zero other test files import `DEFAULT_BUCKET` or assert on the fallback literal.

## Rejection criteria — janitor must PAUSE and escalate to architect if

1. **A production Lambda deploy config sets `ASANA_CACHE_S3_BUCKET=""` (explicit empty string)**. Under Option C this yields `s3.bucket == ""` (Pydantic fallback-on-unset, not fallback-on-empty), which breaks the downstream boto3 `Bucket=""` call. Status quo handlers would have fallen through `or` to `"autom8-s3"`. Verification: grep deploy configs (`/Users/tomtenuta/Code/a8/manifest.yaml`, any Terraform, any GitHub Actions workflow env blocks) for `ASANA_CACHE_S3_BUCKET:` lines and confirm none assign empty string. If found, escalate for Option D re-evaluation.
2. **Grep discovers a third call site** that does `or "autom8-s3"` or imports `DEFAULT_BUCKET`, beyond the three sites enumerated in Scope. Widened blast radius requires re-plan.
3. **`get_settings()` singleton behavior causes the updated test to pass for the wrong reason** — e.g., if `reset_settings()` doesn't actually clear the cache. Verify by running `test_default_bucket_from_settings` in isolation and with pytest-randomly ordering.
4. **Pre-refactor test run fails** (baseline must be green before refactor begins). If `uv run pytest tests/unit/lambda_handlers/test_checkpoint.py tests/unit/lambda_handlers/test_cache_warmer.py` has any red at baseline, that is a separate bug — fix or escalate first.

## Rollback plan

The refactor is one commit. Rollback is `git revert <sha>`. No schema migration, no data change, no config change outside the repo.

If the rollback is triggered by a production Lambda failure (e.g., Rejection criterion 1 surfaces post-deploy):
1. `git revert` the refactor commit on `hygiene/sprint-env-secret-platformization`.
2. Re-deploy Lambdas from the reverted SHA.
3. Open a follow-up ADR documenting the discovered empty-string env config and re-evaluating between Options A/D.

The `S3Settings.bucket` default change is independently reversible — reverting `Field(default="autom8-s3", ...)` back to `Field(default="", ...)` restores prior Pydantic semantics exactly. The handler `or` expressions can be restored from the same revert. No persistent state touched.

## Commit note (for janitor body)

```
refactor(lambda): consolidate autom8-s3 default into S3Settings (RES-002)

Moves the canonical bucket name from two duplicated handler fallbacks into
a single Pydantic default on S3Settings.bucket. Behavior preserved: when
ASANA_CACHE_S3_BUCKET is unset, get_settings().s3.bucket resolves to
"autom8-s3" via Pydantic default instead of via handler-side `or` fallback.

Per ADR-0002 (canonical bucket naming).
Per TDD-lambda-default-bucket-refactor (sprint-D wave 0).
```
