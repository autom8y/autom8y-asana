---
artifact_id: TDD-autom8y-asana-auth-v1-migration
title: "autom8_asana: Migration to autom8y-auth SDK v1.0.0"
created_at: "2026-02-12T22:00:00Z"
author: architect
prd_ref: PRD-autom8y-auth-v1-resilience
status: draft
components:
  - name: jwt_validator
    type: module
    description: "Lazy singleton AuthClient wrapper -- config, initialization, and validate_service_token"
    files:
      - "src/autom8_asana/auth/jwt_validator.py"
  - name: dependencies
    type: module
    description: "FastAPI dependency injection for dual-mode auth (JWT + PAT)"
    files:
      - "src/autom8_asana/api/dependencies.py"
  - name: test_jwt_validator
    type: test
    description: "Unit tests for jwt_validator SDK integration"
    files:
      - "tests/test_auth/test_jwt_validator.py"
  - name: test_integration
    type: test
    description: "Integration tests for dual-mode authentication flow"
    files:
      - "tests/test_auth/test_integration.py"
  - name: test_dependencies
    type: test
    description: "Unit tests for api/dependencies dual-mode auth"
    files:
      - "tests/test_auth/test_dependencies.py"
  - name: pyproject
    type: config
    description: "Dependency version pin update and observability extras"
    files:
      - "pyproject.toml"
schema_version: "1.0"
---

# TDD: autom8_asana Migration to autom8y-auth SDK v1.0.0

## 1. Overview

This TDD specifies the migration of autom8_asana from the deprecated autom8y-auth v0.x API surface (AuthConfig, flat error hierarchy) to the v1.0.0 API surface (AuthSettings, TransientAuthError/PermanentAuthError hierarchy, CircuitOpenError). This is a full modernization migration -- not a feature addition.

**Scope**: 5 source/test files + pyproject.toml. No new features. No new endpoints. No changes to dual-mode token detection logic.

**SDK Reference**: autom8y-auth v1.0.0 (`/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-auth/`)
**SDK TDD Reference**: `TDD-autom8y-auth-v1-resilience`

---

## 2. Dual-Mode Authentication Architecture

This is the most critical section. autom8_asana uses dual-mode authentication: JWT tokens for service-to-service (S2S) calls and Personal Access Tokens (PATs) for user pass-through. The token detection mechanism (dot-counting per ADR-S2S-001) determines which path executes.

### 2.1 Token Detection (UNCHANGED)

The `detect_token_type()` function in `src/autom8_asana/auth/dual_mode.py` counts dots in the bearer token:

- **2 dots** -> `AuthMode.JWT` (header.payload.signature)
- **0 dots** -> `AuthMode.PAT` (format: `0/xxxxxxxx` or `1/xxxxxxxx`)

This function does NOT change in this migration. It is upstream of all auth logic.

### 2.2 Error Path Boundary Diagram

```
Bearer Token
    |
    v
detect_token_type(token)  [dual_mode.py -- UNCHANGED]
    |
    +----- AuthMode.PAT ------> PAT Path (pass-through)
    |                               |
    |                               v
    |                           Return AuthContext(mode=PAT, asana_pat=token)
    |                           [NO SDK errors possible]
    |                           [NO CircuitOpenError possible]
    |                           [NO TransientAuthError possible]
    |                           [NO PermanentAuthError possible]
    |
    +----- AuthMode.JWT ------> JWT Path (SDK validation)
                                    |
                                    v
                                validate_service_token(token)  [jwt_validator.py]
                                    |
                                    v
                                AuthClient.validate_service_token(token)  [SDK]
                                    |
                                    +--- JWKS fetch (retry + circuit breaker + stale cache)
                                    |       |
                                    |       +--- CircuitOpenError  [TransientAuthError, 503]
                                    |       +--- JWKSFetchError    [TransientAuthError, 503]
                                    |
                                    +--- Token validation
                                            |
                                            +--- TokenExpiredError       [PermanentAuthError, 401]
                                            +--- InvalidSignatureError   [PermanentAuthError, 401]
                                            +--- InvalidTokenError       [PermanentAuthError, 401]
                                            +--- InvalidIssuerError      [PermanentAuthError, 401]
                                            +--- UnknownKeyIDError       [PermanentAuthError, 401]
                                            +--- InvalidAlgorithmError   [PermanentAuthError, 401]
                                            +--- InvalidTokenTypeError   [PermanentAuthError, 401]
                                            +--- MissingTokenError       [PermanentAuthError, 401]
```

### 2.3 Critical Invariant: CircuitOpenError Scope

**CircuitOpenError can ONLY surface in the JWT path.** It is raised by the SDK's internal JWKS client when the circuit breaker is open. The PAT path never touches the SDK, never fetches JWKS, and therefore can never trigger a circuit breaker.

This invariant is structural: `get_auth_context()` in `dependencies.py` returns early for PAT tokens (line 153-162 in current code) before any SDK call is made. The migration preserves this early-return structure.

### 2.4 Error Handling by Path

| Error Type | JWT Path | PAT Path | Rationale |
|------------|----------|----------|-----------|
| `CircuitOpenError` | YES (503) | NEVER | Circuit breaker is internal to JWKS fetch |
| `JWKSFetchError` | YES (503) | NEVER | JWKS fetch only happens for JWT validation |
| `TransientAuthError` (catch-all) | YES (503) | NEVER | All transient errors come from JWKS operations |
| `PermanentAuthError` (catch-all) | YES (401) | NEVER | All permanent errors come from token validation |
| `TokenExpiredError` | YES (401) | NEVER | JWT expiry check is SDK-side |
| `InvalidSignatureError` | YES (401) | NEVER | Signature check is SDK-side |
| `InvalidTokenError` | YES (401) | NEVER | Token parsing is SDK-side |
| `BotPATError` | YES (503) | NEVER | Bot PAT is only needed in JWT mode |
| `HTTPException` (header validation) | YES | YES | Pre-detection header checks apply to both |

---

## 3. Error Hierarchy Mapping

### 3.1 Existing Errors -> v1.0 Classification

| Current Error | v1.0 Parent | Path | HTTP Status | Notes |
|---|---|---|---|---|
| `AuthError` | (unchanged, root) | Both (catch-all) | 401 | Base catch still works: `except AuthError` |
| `TokenExpiredError` | `PermanentAuthError` | JWT only | 401 | Was direct child of `AuthError`, now grandchild |
| `InvalidSignatureError` | `PermanentAuthError` | JWT only | 401 | Was direct child of `AuthError`, now grandchild |
| `InvalidTokenError` | `PermanentAuthError` | JWT only | 401 | Was direct child of `AuthError`, now grandchild |
| `JWKSFetchError` | `TransientAuthError` | JWT only | 503 | Was direct child of `AuthError`, now grandchild |

### 3.2 New Errors to Handle

| New Error | v1.0 Parent | Path | HTTP Status | Notes |
|---|---|---|---|---|
| `CircuitOpenError` | `TransientAuthError` | JWT only | 503 | Circuit breaker is open; fail-fast, no JWKS fetch attempted |
| `TransientAuthError` | `AuthError` | JWT only | 503 | New intermediate catch: retryable errors |
| `PermanentAuthError` | `AuthError` | JWT only | 401 | New intermediate catch: non-retryable errors |

### 3.3 Catch Strategy in dependencies.py

The current code uses a broad `except Exception` with runtime `isinstance(e, AuthError)` check. The migration replaces this with explicit, ordered exception handlers:

```python
# NEW: Ordered from most specific to least specific
except CircuitOpenError as e:
    # JWT path only -- JWKS endpoint unavailable, 503
except TransientAuthError as e:
    # JWT path only -- retryable infra errors, 503
except PermanentAuthError as e:
    # JWT path only -- bad token, 401
except AuthError as e:
    # Catch-all safety net for any future AuthError subclass, 401
```

---

## 4. File-by-File Transformation Map

### 4.1 File 1: `src/autom8_asana/auth/jwt_validator.py`

**Absolute path**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/auth/jwt_validator.py`

#### Current State

- **Imports**: `AuthClient` and `ServiceClaims` via `TYPE_CHECKING`; `AuthClient` and `AuthConfig` imported lazily inside `_get_auth_client()`
- **Singleton pattern**: Module-level `_auth_client: AuthClient | None = None` with lazy init in `_get_auth_client()`
- **Config**: `AuthConfig.from_env()` -- deprecated v0.x API
- **Validation**: `client.validate_service_token(token)` -- unchanged SDK method
- **Reset**: `reset_auth_client()` clears singleton for testing

#### Target State

- **Imports**: Replace `AuthConfig` with `AuthSettings` in lazy import
- **Singleton pattern**: Same lazy singleton structure, but using `AuthSettings()` instead of `AuthConfig.from_env()`
- **Config**: `AuthSettings()` -- v1.0 API, reads `AUTH__*` env vars automatically
- **Validation**: `client.validate_service_token(token)` -- no change (SDK method signature is preserved)
- **Logging**: Log `AuthSettings` fields instead of `AuthConfig` fields

#### Migration Steps

1. In `_get_auth_client()`, change the lazy import from `AuthConfig` to `AuthSettings`.
2. Replace `config = AuthConfig.from_env()` with `settings = AuthSettings()`.
3. Replace `_auth_client = AuthClient(config)` with `_auth_client = AuthClient(settings)`.
4. Update the logger extra dict to use `settings` field names (they are the same: `issuer`, `jwks_url`, `dev_mode`).
5. Update the module docstring to reference `AuthSettings` instead of `AuthConfig.from_env()`.
6. No changes to `validate_service_token()` signature or body.
7. No changes to `reset_auth_client()`.

#### Before/After: `_get_auth_client()`

**BEFORE:**
```python
def _get_auth_client() -> AuthClient:
    global _auth_client
    if _auth_client is None:
        from autom8y_auth import AuthClient, AuthConfig

        config = AuthConfig.from_env()
        _auth_client = AuthClient(config)
        logger.debug(
            "auth_client_initialized",
            extra={
                "issuer": config.issuer,
                "jwks_url": config.jwks_url,
                "dev_mode": config.dev_mode,
            },
        )
    return _auth_client
```

**AFTER:**
```python
def _get_auth_client() -> AuthClient:
    global _auth_client
    if _auth_client is None:
        from autom8y_auth import AuthClient, AuthSettings

        settings = AuthSettings()
        _auth_client = AuthClient(settings)
        logger.debug(
            "auth_client_initialized",
            extra={
                "issuer": settings.issuer,
                "jwks_url": settings.jwks_url,
                "dev_mode": settings.dev_mode,
            },
        )
    return _auth_client
```

#### What Does NOT Change

- `validate_service_token()` function signature: `async def validate_service_token(token: str) -> ServiceClaims`
- `reset_auth_client()` function
- Module-level `_auth_client` variable type annotation
- The `TYPE_CHECKING` imports (`AuthClient`, `ServiceClaims`)
- The `__all__` export list

---

### 4.2 File 2: `src/autom8_asana/api/dependencies.py`

**Absolute path**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py`

#### Current State

- **Error handling in `get_auth_context()`**: Uses `except Exception as e` with runtime `isinstance(e, AuthError)` check inside a nested try/except block
- **All AuthErrors map to 401**: No distinction between transient and permanent errors
- **No CircuitOpenError handling**: The error did not exist in v0.x
- **Import pattern**: `from autom8y_auth import AuthError` inside the exception handler

#### Target State

- **Error handling**: Explicit, ordered exception handlers for `CircuitOpenError`, `TransientAuthError`, `PermanentAuthError`
- **CircuitOpenError -> 503**: Transient infrastructure errors return 503
- **PermanentAuthError -> 401**: Token validation failures return 401
- **Import pattern**: Top-level imports from `autom8y_auth` for error types (moved out of exception handler)

#### Migration Steps

1. Add top-level imports for SDK error types (inside `TYPE_CHECKING` is not sufficient since they are used at runtime in `except` clauses).
2. Replace the broad `except Exception as e` block in `get_auth_context()` with three ordered handlers.
3. First handler: `except CircuitOpenError as e` -> HTTP 503 with error code `CIRCUIT_OPEN`.
4. Second handler: `except TransientAuthError as e` -> HTTP 503 with the error's `.code` attribute.
5. Third handler: `except PermanentAuthError as e` -> HTTP 401 with the error's `.code` attribute.
6. Fourth handler (safety net): `except AuthError as e` -> HTTP 401 (catch-all for any future error subclass).
7. Remove the nested try/except `ImportError` guard for `from autom8y_auth import AuthError` (it was only needed because the import was inside the handler; with top-level imports, ImportError will surface at module load if the SDK is missing -- which is the correct behavior since auth is a required capability).
8. Remove the `except Exception` fallback for non-AuthError exceptions (these should propagate as 500 via FastAPI's default handler, not be caught and re-wrapped).

#### Before/After: JWT Error Handling in `get_auth_context()`

**BEFORE** (lines 165-220):
```python
    # JWT mode: validate token, then use bot PAT
    try:
        from ..auth.jwt_validator import validate_service_token
        claims = await validate_service_token(token)
    except ImportError as e:
        logger.error("autom8y_auth_not_installed", extra={"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=503, detail={"error": "S2S_NOT_CONFIGURED", "message": "..."})
    except Exception as e:
        try:
            from autom8y_auth import AuthError
            if isinstance(e, AuthError):
                logger.warning("s2s_jwt_validation_failed", extra={"request_id": request_id, "error_code": e.code, "error_message": str(e)})
                raise HTTPException(status_code=401, detail={"error": e.code, "message": "JWT validation failed"})
        except ImportError:
            pass
        logger.exception("s2s_jwt_validation_unexpected_error", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "Authentication error"})
```

**AFTER:**
```python
    # JWT mode: validate token, then use bot PAT
    try:
        from ..auth.jwt_validator import validate_service_token
        claims = await validate_service_token(token)
    except ImportError as e:
        logger.error("autom8y_auth_not_installed", extra={"request_id": request_id, "error": str(e)})
        raise HTTPException(
            status_code=503,
            detail={"error": "S2S_NOT_CONFIGURED", "message": "Service-to-service authentication is not available"},
        )
    except CircuitOpenError as e:
        logger.warning(
            "s2s_circuit_open",
            extra={"request_id": request_id, "error_code": e.code, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=503,
            detail={"error": e.code, "message": "Authentication service temporarily unavailable"},
        )
    except TransientAuthError as e:
        logger.warning(
            "s2s_transient_auth_error",
            extra={"request_id": request_id, "error_code": e.code, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=503,
            detail={"error": e.code, "message": "Authentication service temporarily unavailable"},
        )
    except PermanentAuthError as e:
        logger.warning(
            "s2s_jwt_validation_failed",
            extra={"request_id": request_id, "error_code": e.code, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=401,
            detail={"error": e.code, "message": "JWT validation failed"},
        )
    except AuthError as e:
        logger.warning(
            "s2s_jwt_validation_failed",
            extra={"request_id": request_id, "error_code": e.code, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=401,
            detail={"error": e.code, "message": "JWT validation failed"},
        )
```

#### New Top-Level Import

Add after the existing imports at the top of the file:

```python
from autom8y_auth import (
    AuthError,
    CircuitOpenError,
    PermanentAuthError,
    TransientAuthError,
)
```

This import replaces the runtime `from autom8y_auth import AuthError` that was previously inside the exception handler.

**Note on ImportError**: The current code guards against `autom8y_auth` not being installed. With top-level imports, if the SDK is missing, the module will fail to import entirely. This is the correct behavior: `autom8y_auth` is listed in `pyproject.toml [project.optional-dependencies] auth` and is required for any JWT-authenticated endpoint to function. The `except ImportError` handler for `validate_service_token` is preserved since that is a lazy import from a sibling module.

#### What Does NOT Change

- `_extract_bearer_token()` function
- `AuthContext` class
- `get_asana_pat()` function
- `get_asana_client()` function
- `get_asana_client_from_context()` function
- `get_mutation_invalidator()` function
- `get_request_id()` function
- All type aliases (`AsanaPAT`, `AsanaClientDep`, etc.)
- All service factory functions (`get_entity_service`, `get_task_service`, `get_section_service`)
- The PAT early-return path in `get_auth_context()` (lines 153-162)
- The `__all__` export list

---

### 4.3 File 3: `tests/test_auth/test_jwt_validator.py`

**Absolute path**: `/Users/tomtenuta/Code/autom8_asana/tests/test_auth/test_jwt_validator.py`

#### Current State

- **Imports**: `AuthError`, `InvalidTokenError` from `autom8y_auth` (inside test methods)
- **Tests**: `TestResetAuthClient` (2 tests), `TestValidateServiceTokenIntegration` (2 tests)
- **Error assertions**: `pytest.raises(AuthError)`, `pytest.raises(InvalidTokenError)`

#### Target State

- **Imports**: Same error types still importable and usable (the SDK preserves all leaf error types)
- **Tests**: Existing tests remain valid since `AuthError` and `InvalidTokenError` still exist in v1.0
- **New tests**: Add tests verifying `AuthSettings` is used (not `AuthConfig`)

#### Migration Steps

1. No changes needed to existing tests -- `AuthError` and `InvalidTokenError` are preserved in v1.0.
2. Add a new test class `TestAuthClientUsesSettings` to verify the singleton uses `AuthSettings`.
3. Add a test that verifies `AuthConfig.from_env()` is NOT called (i.e., no deprecation warning).

#### New Tests to Add

```python
class TestAuthClientUsesSettings:
    """Verify jwt_validator uses AuthSettings (v1.0), not AuthConfig (deprecated)."""

    def test_no_deprecation_warning_on_init(self) -> None:
        """Initializing auth client does not trigger AuthConfig deprecation warning."""
        import warnings

        from autom8_asana.auth.jwt_validator import _get_auth_client

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                _get_auth_client()
            except Exception:
                pass  # JWKS fetch may fail in test env
            deprecation_warnings = [
                x for x in w
                if issubclass(x.category, DeprecationWarning)
                and "AuthConfig" in str(x.message)
            ]
            assert len(deprecation_warnings) == 0, (
                "AuthConfig deprecation warning detected -- "
                "jwt_validator should use AuthSettings, not AuthConfig"
            )
```

---

### 4.4 File 4: `tests/test_auth/test_integration.py`

**Absolute path**: `/Users/tomtenuta/Code/autom8_asana/tests/test_auth/test_integration.py`

#### Current State

- **Imports**: `TokenExpiredError`, `InvalidSignatureError` from `autom8y_auth` (inside test methods)
- **Mock pattern**: `patch("autom8_asana.auth.jwt_validator.validate_service_token", side_effect=TokenExpiredError(...))`
- **Error assertions**: Checks `response.json()["detail"]["error"]` against error `.code` values like `"TOKEN_EXPIRED"`, `"INVALID_SIGNATURE"`

#### Target State

- **Imports**: Same error types still importable (SDK preserves all leaf types)
- **Mock pattern**: Unchanged (mocks bypass SDK internals)
- **Error assertions**: Unchanged (`.code` attributes are identical in v1.0)
- **New tests**: Add `CircuitOpenError` test, add `TransientAuthError` distinction test

#### Migration Steps

1. Existing tests for `TokenExpiredError` and `InvalidSignatureError` require NO changes. These error types still exist in v1.0 with the same `.code` attributes and are now subclasses of `PermanentAuthError`. The mock pattern patches `validate_service_token` directly, so it does not exercise the real SDK.
2. Add new test class `TestCircuitOpenError` for CircuitOpenError -> 503 mapping.
3. Add new test class `TestTransientVsPermanentErrors` for error classification.
4. Add new test to verify PAT path is unaffected by circuit breaker state.

#### New Tests to Add

```python
class TestCircuitOpenError:
    """Test CircuitOpenError in JWT path returns 503."""

    def test_circuit_open_returns_503(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CircuitOpenError returns 503, not 401."""
        client = TestClient(app)
        jwt_token = "header.payload.signature"

        from autom8y_auth import CircuitOpenError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=CircuitOpenError("Circuit breaker is open"),
        ):
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "CIRCUIT_OPEN"

    def test_pat_unaffected_by_circuit_state(self, app: FastAPI) -> None:
        """PAT tokens work regardless of circuit breaker state.

        This test verifies the critical invariant: CircuitOpenError
        can never surface in the PAT path.
        """
        client = TestClient(app)
        pat_token = "0/1234567890abcdef1234567890"

        # Even if we could hypothetically set the circuit to open,
        # PAT path never touches the SDK, so it always succeeds.
        response = client.get(
            "/test", headers={"Authorization": f"Bearer {pat_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "pat"


class TestTransientVsPermanentErrors:
    """Test that transient errors return 503 and permanent errors return 401."""

    def test_jwks_fetch_error_returns_503(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JWKSFetchError (transient) returns 503."""
        client = TestClient(app)
        jwt_token = "header.payload.signature"

        from autom8y_auth import JWKSFetchError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=JWKSFetchError("JWKS endpoint unreachable"),
        ):
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "JWKS_FETCH_ERROR"

    def test_expired_token_returns_401(
        self, app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TokenExpiredError (permanent) returns 401."""
        client = TestClient(app)
        jwt_token = "header.payload.signature"

        from autom8y_auth import TokenExpiredError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=TokenExpiredError("Token has expired"),
        ):
            response = client.get(
                "/test", headers={"Authorization": f"Bearer {jwt_token}"}
            )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "TOKEN_EXPIRED"
```

#### Existing Tests: No Changes Required

The following existing tests require no modifications:

- `TestPATPassThrough.test_pat_accepted_and_passed_through` -- PAT path unchanged
- `TestPATPassThrough.test_pat_with_1_prefix_accepted` -- PAT path unchanged
- `TestJWTMode.test_valid_jwt_accepted` -- Mock bypasses error handling
- `TestJWTMode.test_expired_jwt_returns_401` -- `TokenExpiredError` still exists, still has `.code == "TOKEN_EXPIRED"`, status remains 401
- `TestJWTMode.test_invalid_signature_returns_401` -- `InvalidSignatureError` still exists, still has `.code == "INVALID_SIGNATURE"`, status remains 401
- `TestJWTMode.test_missing_bot_pat_returns_503` -- Bot PAT path unchanged
- `TestMissingAuth.*` -- Header validation path unchanged
- `TestBotPatSecurity.*` -- Security tests unchanged

---

### 4.5 File 5: `tests/test_auth/test_dependencies.py`

**Absolute path**: `/Users/tomtenuta/Code/autom8_asana/tests/test_auth/test_dependencies.py`

#### Current State

- **Imports**: `TokenExpiredError` from `autom8y_auth` (inside test method)
- **Mock pattern**: Same as test_integration.py
- **Error assertion**: Checks `status_code == 401` and `detail["error"] == "TOKEN_EXPIRED"`

#### Target State

- Existing test for `TokenExpiredError` requires NO changes (error type preserved, code preserved, still maps to 401)
- Add new tests for `CircuitOpenError -> 503` and transient/permanent distinction

#### Migration Steps

1. Existing `test_jwt_validation_failure_returns_401` requires no changes.
2. Add new test methods for `CircuitOpenError` and `TransientAuthError` handling.

#### New Tests to Add

```python
class TestGetAuthContextCircuitOpen:
    """Test CircuitOpenError handling in get_auth_context."""

    @pytest.mark.asyncio
    async def test_circuit_open_returns_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CircuitOpenError maps to HTTP 503."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-circuit-open"
        jwt_token = "header.payload.signature"

        from autom8y_auth import CircuitOpenError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=CircuitOpenError("Circuit breaker is open (failed 5 times)"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["error"] == "CIRCUIT_OPEN"

    @pytest.mark.asyncio
    async def test_jwks_fetch_error_returns_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JWKSFetchError (transient) maps to HTTP 503."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-jwks-fetch-error"
        jwt_token = "header.payload.signature"

        from autom8y_auth import JWKSFetchError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=JWKSFetchError("JWKS endpoint unreachable"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["error"] == "JWKS_FETCH_ERROR"

    @pytest.mark.asyncio
    async def test_permanent_error_returns_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PermanentAuthError subclasses map to HTTP 401."""
        mock_request = MagicMock()
        mock_request.state.request_id = "test-permanent-error"
        jwt_token = "header.payload.signature"

        from autom8y_auth import InvalidSignatureError

        with patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            new_callable=AsyncMock,
            side_effect=InvalidSignatureError("Signature verification failed"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request=mock_request, token=jwt_token)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["error"] == "INVALID_SIGNATURE"
```

#### Existing Tests: No Changes Required

- `TestExtractBearerToken.*` -- Header extraction unchanged
- `TestAuthContext.*` -- `AuthContext` class unchanged
- `TestGetAuthContextPATMode.*` -- PAT path unchanged
- `TestGetAuthContextJWTMode.test_jwt_validated_and_bot_pat_used` -- Mock bypasses error handling
- `TestGetAuthContextJWTMode.test_jwt_validation_failure_returns_401` -- `TokenExpiredError` still returns 401 with `.code == "TOKEN_EXPIRED"`
- `TestGetAuthContextJWTMode.test_missing_bot_pat_returns_503` -- Bot PAT path unchanged
- `TestBotPatNeverLogged.*` -- Security tests unchanged

---

## 5. Lazy Singleton Replacement

### 5.1 Current Pattern

File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/auth/jwt_validator.py`

```python
# Module-level client (lazy initialized, thread-safe)
_auth_client: AuthClient | None = None

def _get_auth_client() -> AuthClient:
    global _auth_client
    if _auth_client is None:
        from autom8y_auth import AuthClient, AuthConfig
        config = AuthConfig.from_env()
        _auth_client = AuthClient(config)
        # ... logging ...
    return _auth_client
```

**Characteristics**:
- Lazy: Client is created on first call, not at module import
- Singleton: Module-level variable ensures one instance per process
- Thread safety: Python's GIL provides basic thread safety for the `if _auth_client is None` check; for asyncio, coroutines cannot be preempted during synchronous code, so the check-and-assign is atomic within an event loop
- Import-time deferral: `autom8y_auth` is imported inside the function to avoid import-time side effects

### 5.2 New Pattern

```python
# Module-level client (lazy initialized)
_auth_client: AuthClient | None = None

def _get_auth_client() -> AuthClient:
    global _auth_client
    if _auth_client is None:
        from autom8y_auth import AuthClient, AuthSettings
        settings = AuthSettings()
        _auth_client = AuthClient(settings)
        logger.debug(
            "auth_client_initialized",
            extra={
                "issuer": settings.issuer,
                "jwks_url": settings.jwks_url,
                "dev_mode": settings.dev_mode,
            },
        )
    return _auth_client
```

### 5.3 Thread Safety Considerations

No changes. The singleton initialization is synchronous code inside an `async` function call chain. In asyncio, coroutines execute cooperatively -- the `if _auth_client is None` check and the subsequent assignment cannot be interleaved by another coroutine because there is no `await` between the check and the assignment. The `AuthSettings()` constructor and `AuthClient(settings)` constructor are both synchronous and complete atomically from the event loop's perspective.

### 5.4 Initialization Timing

**Unchanged: Lazy initialization.** The client is created on the first call to `validate_service_token()`, which is the first JWT-authenticated request. This is intentional:

- PAT-only requests never trigger client creation
- No startup cost if JWT auth is not used
- The SDK's `warmup()` method exists for eager initialization, but autom8_asana does not use it (and this migration does not add it)

### 5.5 FastAPI Dependency Injection Interaction

The singleton interacts with FastAPI's DI chain as follows:

```
HTTP Request
    -> get_auth_context(request, token)           [FastAPI DI]
        -> detect_token_type(token)               [dual_mode.py]
        -> validate_service_token(token)          [jwt_validator.py]
            -> _get_auth_client()                 [singleton init or return]
            -> client.validate_service_token()    [SDK call]
```

The singleton is process-global, not request-scoped. This is correct because `AuthClient` is designed to be long-lived (it owns the JWKS cache, circuit breaker state, and HTTP client). Creating a new `AuthClient` per request would defeat caching and circuit breaker tracking.

---

## 6. `validate_service_token()` Changes

### 6.1 Current Signature

```python
async def validate_service_token(token: str) -> ServiceClaims:
```

### 6.2 Target Signature

```python
async def validate_service_token(token: str) -> ServiceClaims:
```

**The signature does NOT change.** The function is a thin wrapper around `AuthClient.validate_service_token()`, which also has an unchanged signature in v1.0.

### 6.3 Error Propagation

The function does NOT wrap or re-raise SDK errors. It lets them propagate directly to the caller (`get_auth_context()` in `dependencies.py`), which handles the HTTP mapping.

**Current behavior**: SDK errors propagate unmodified.
**Target behavior**: SDK errors propagate unmodified. The new error types (`CircuitOpenError`, `TransientAuthError`, `PermanentAuthError`) are handled by the updated `get_auth_context()`.

### 6.4 What the Function Does NOT Do

- Does NOT catch any SDK errors
- Does NOT map errors to HTTP status codes (that is the responsibility of `dependencies.py`)
- Does NOT log errors (success logging only; error logging is done by the caller)
- Does NOT wrap SDK errors in custom exception types

---

## 7. AuthSettings Configuration

### 7.1 Complete AuthSettings Instantiation for autom8_asana

autom8_asana uses zero-config instantiation. All values come from environment variables or SDK defaults:

```python
settings = AuthSettings()
```

This is equivalent to:

```python
settings = AuthSettings(
    jwks_url="https://auth.api.autom8y.io/.well-known/jwks.json",  # or AUTH__JWKS_URL
    issuer="auth.api.autom8y.io",                                    # or AUTH__ISSUER
    require_access_token_type=True,                                  # or AUTH__REQUIRE_ACCESS_TOKEN_TYPE
    algorithms=("RS256",),
    dev_mode=False,                                                  # or AUTH__DEV_MODE
    http_timeout_seconds=10.0,                                       # or AUTH__HTTP_TIMEOUT_SECONDS
    retry=RetrySettings(
        max_attempts=3,                    # or AUTH__RETRY__MAX_ATTEMPTS
        base_delay_seconds=0.5,            # or AUTH__RETRY__BASE_DELAY_SECONDS
        max_delay_seconds=10.0,            # or AUTH__RETRY__MAX_DELAY_SECONDS
        retry_on_status_codes=[429, 500, 502, 503, 504],
    ),
    circuit_breaker=CircuitBreakerSettings(
        failure_threshold=5,               # or AUTH__CIRCUIT_BREAKER__FAILURE_THRESHOLD
        recovery_timeout_seconds=30.0,     # or AUTH__CIRCUIT_BREAKER__RECOVERY_TIMEOUT_SECONDS
    ),
    cache=CacheSettings(
        ttl_seconds=300,                   # or AUTH__CACHE__TTL_SECONDS
        stale_ttl_seconds=300,             # or AUTH__CACHE__STALE_TTL_SECONDS
    ),
    observability=ObservabilitySettings(
        logging_enabled=True,              # or AUTH__OBSERVABILITY__LOGGING_ENABLED
        tracing_enabled=True,              # or AUTH__OBSERVABILITY__TRACING_ENABLED
        metrics_enabled=True,              # or AUTH__OBSERVABILITY__METRICS_ENABLED
    ),
)
```

### 7.2 Why Zero-Config is Sufficient

autom8_asana does not need to customize any resilience parameters. The SDK defaults are tuned for production S2S workloads:

- **3 retry attempts** with exponential backoff is appropriate for JWKS fetch (transient network blips)
- **5 failure threshold** before circuit opens prevents slow cascading failures
- **30s recovery timeout** balances fail-fast with recovery opportunity
- **300s cache TTL + 300s stale TTL** means keys are valid for up to 10 minutes total during outage
- **Observability enabled** by default, which is appropriate since autom8_asana already depends on `autom8y-log` and `autom8y-telemetry`

### 7.3 How AuthSettings Replaces AuthConfig.from_env()

| AuthConfig.from_env() | AuthSettings() |
|---|---|
| Manually reads `os.getenv("AUTH_JWKS_URL", ...)` | Pydantic-settings reads `AUTH__JWKS_URL` automatically |
| Returns frozen dataclass | Returns Pydantic BaseSettings instance |
| No nested config (flat fields only) | Supports nested `RetrySettings`, `CircuitBreakerSettings`, etc. |
| No validation beyond basic range checks | Pydantic field validators with explicit ranges |
| Triggers deprecation warning in v1.0 | No deprecation warning |

---

## 8. Environment Variable Migration

### 8.1 Complete Before/After Table

| Purpose | Old Env Var (v0.x) | New Env Var (v1.0) | Default | Notes |
|---|---|---|---|---|
| JWKS endpoint URL | `AUTH_JWKS_URL` | `AUTH__JWKS_URL` | `https://auth.api.autom8y.io/.well-known/jwks.json` | Legacy name aliased with deprecation warning |
| JWKS cache TTL | `AUTH_JWKS_CACHE_TTL` | `AUTH__CACHE__TTL_SECONDS` | `300` | Name changed; legacy aliased |
| Token issuer | `AUTH_ISSUER` | `AUTH__ISSUER` | `auth.api.autom8y.io` | Legacy aliased |
| Require access token type | `AUTH_REQUIRE_ACCESS_TOKEN` | `AUTH__REQUIRE_ACCESS_TOKEN_TYPE` | `true` | Legacy aliased |
| Dev mode | `AUTH_DEV_MODE` | `AUTH__DEV_MODE` | `false` | Legacy aliased |
| HTTP timeout | `AUTH_HTTP_TIMEOUT` | `AUTH__HTTP_TIMEOUT_SECONDS` | `10.0` | Legacy aliased |
| Retry max attempts | (not available) | `AUTH__RETRY__MAX_ATTEMPTS` | `3` | New in v1.0 |
| Retry base delay | (not available) | `AUTH__RETRY__BASE_DELAY_SECONDS` | `0.5` | New in v1.0 |
| Retry max delay | (not available) | `AUTH__RETRY__MAX_DELAY_SECONDS` | `10.0` | New in v1.0 |
| Circuit breaker threshold | (not available) | `AUTH__CIRCUIT_BREAKER__FAILURE_THRESHOLD` | `5` | New in v1.0 |
| Circuit breaker recovery | (not available) | `AUTH__CIRCUIT_BREAKER__RECOVERY_TIMEOUT_SECONDS` | `30.0` | New in v1.0 |
| Stale cache TTL | (not available) | `AUTH__CACHE__STALE_TTL_SECONDS` | `300` | New in v1.0 |
| Logging enabled | (not available) | `AUTH__OBSERVABILITY__LOGGING_ENABLED` | `true` | New in v1.0 |
| Tracing enabled | (not available) | `AUTH__OBSERVABILITY__TRACING_ENABLED` | `true` | New in v1.0 |
| Metrics enabled | (not available) | `AUTH__OBSERVABILITY__METRICS_ENABLED` | `true` | New in v1.0 |

### 8.2 Migration Strategy

The SDK's `AuthSettings._apply_legacy_env_vars()` model validator handles backward compatibility: if `AUTH_JWKS_URL` is set but `AUTH__JWKS_URL` is not, it maps the legacy value and emits a deprecation warning. This means:

1. **No immediate env var changes required** in autom8_asana's deployment config
2. Legacy env vars will continue to work
3. Deprecation warnings will appear in logs
4. The deployment team should update env vars to the new format at their convenience

### 8.3 Non-Auth Env Vars (UNCHANGED)

The following env var is NOT part of the auth SDK migration:

| Env Var | Purpose | Unchanged? |
|---|---|---|
| `ASANA_PAT` | Bot PAT for S2S mode | YES -- used by `bot_pat.py`, not the auth SDK |

---

## 9. pyproject.toml Changes

**Absolute path**: `/Users/tomtenuta/Code/autom8_asana/pyproject.toml`

### 9.1 Version Pin Update

**BEFORE:**
```toml
auth = [
    "autom8y-auth>=0.1.0",
]
```

**AFTER:**
```toml
auth = [
    "autom8y-auth[observability]>=1.0.0",
]
```

### 9.2 Dev Dependency Update

**BEFORE:**
```toml
    "autom8y-auth>=0.1.0",  # Required for test_auth tests
```

**AFTER:**
```toml
    "autom8y-auth[observability]>=1.0.0",  # Required for test_auth tests
```

### 9.3 Rationale for `[observability]` Extra

autom8_asana already depends on `autom8y-log>=0.3.2` and `autom8y-telemetry[fastapi]>=0.2.0` as core dependencies. Adding `[observability]` to the auth SDK extra ensures the auth SDK's structured logging and tracing are active (rather than falling back to stdlib). This adds no new transitive dependencies since both packages are already installed.

---

## 10. Test Transformation Guide

### 10.1 `test_jwt_validator.py` Changes

| Test | Change Required | Reason |
|---|---|---|
| `TestResetAuthClient.test_reset_clears_singleton` | None | `reset_auth_client()` is unchanged |
| `TestResetAuthClient.test_reset_is_idempotent` | None | `reset_auth_client()` is unchanged |
| `TestValidateServiceTokenIntegration.test_validate_invalid_token_format` | None | `AuthError` is still the root exception type |
| `TestValidateServiceTokenIntegration.test_validate_malformed_jwt` | None | `InvalidTokenError` is still a leaf exception type |
| **NEW**: `TestAuthClientUsesSettings.test_no_deprecation_warning_on_init` | Add | Verify `AuthSettings` used instead of `AuthConfig` |

### 10.2 `test_integration.py` Changes

| Test | Change Required | Reason |
|---|---|---|
| `TestPATPassThrough.*` (2 tests) | None | PAT path unchanged |
| `TestJWTMode.test_valid_jwt_accepted` | None | Mock bypasses error handling |
| `TestJWTMode.test_expired_jwt_returns_401` | None | `TokenExpiredError` preserved, `.code` preserved, HTTP 401 preserved |
| `TestJWTMode.test_invalid_signature_returns_401` | None | `InvalidSignatureError` preserved, `.code` preserved, HTTP 401 preserved |
| `TestJWTMode.test_missing_bot_pat_returns_503` | None | Bot PAT path unchanged |
| `TestMissingAuth.*` (4 tests) | None | Header validation unchanged |
| `TestBotPatSecurity.*` (2 tests) | None | Security tests unchanged |
| **NEW**: `TestCircuitOpenError.test_circuit_open_returns_503` | Add | Verify `CircuitOpenError` -> 503 |
| **NEW**: `TestCircuitOpenError.test_pat_unaffected_by_circuit_state` | Add | Verify PAT path isolation from circuit breaker |
| **NEW**: `TestTransientVsPermanentErrors.test_jwks_fetch_error_returns_503` | Add | Verify `JWKSFetchError` -> 503 |
| **NEW**: `TestTransientVsPermanentErrors.test_expired_token_returns_401` | Add | Verify `TokenExpiredError` -> 401 via `PermanentAuthError` path |

### 10.3 `test_dependencies.py` Changes

| Test | Change Required | Reason |
|---|---|---|
| `TestExtractBearerToken.*` (5 tests) | None | `_extract_bearer_token()` unchanged |
| `TestAuthContext.*` (2 tests) | None | `AuthContext` class unchanged |
| `TestGetAuthContextPATMode.*` (2 tests) | None | PAT path unchanged |
| `TestGetAuthContextJWTMode.test_jwt_validated_and_bot_pat_used` | None | Mock bypasses error handling |
| `TestGetAuthContextJWTMode.test_jwt_validation_failure_returns_401` | None | `TokenExpiredError` -> 401 preserved |
| `TestGetAuthContextJWTMode.test_missing_bot_pat_returns_503` | None | Bot PAT path unchanged |
| `TestBotPatNeverLogged.*` (1 test) | None | Security tests unchanged |
| **NEW**: `TestGetAuthContextCircuitOpen.test_circuit_open_returns_503` | Add | Verify `CircuitOpenError` -> 503 at dependency level |
| **NEW**: `TestGetAuthContextCircuitOpen.test_jwks_fetch_error_returns_503` | Add | Verify `JWKSFetchError` -> 503 at dependency level |
| **NEW**: `TestGetAuthContextCircuitOpen.test_permanent_error_returns_401` | Add | Verify `PermanentAuthError` -> 401 at dependency level |

### 10.4 Summary of New Tests

| Test File | New Test Class | New Test Count | Purpose |
|---|---|---|---|
| `test_jwt_validator.py` | `TestAuthClientUsesSettings` | 1 | Verify no `AuthConfig` deprecation warning |
| `test_integration.py` | `TestCircuitOpenError` | 2 | `CircuitOpenError` -> 503, PAT path isolation |
| `test_integration.py` | `TestTransientVsPermanentErrors` | 2 | Transient -> 503, Permanent -> 401 |
| `test_dependencies.py` | `TestGetAuthContextCircuitOpen` | 3 | `CircuitOpenError`/`JWKSFetchError` -> 503, `PermanentAuthError` -> 401 |
| **Total** | | **8** | |

---

## 11. Implementation Sequence

The implementation must follow this order due to import dependencies:

### Phase 1: `pyproject.toml`

Update the version pin first so the SDK is available at the correct version.

### Phase 2: `jwt_validator.py`

Replace `AuthConfig.from_env()` with `AuthSettings()`. This is the foundation -- all other changes depend on the SDK being initialized via v1.0 config.

### Phase 3: `dependencies.py`

Add top-level imports for error types and replace the broad exception handler. This is the most complex change and the one most likely to introduce bugs if the error handler ordering is wrong.

### Phase 4: Test files

Update all three test files: add new tests, verify existing tests still pass.

### Phase 5: Verification

Run the full test suite. Verify:
- No `AuthConfig` deprecation warnings in test output
- All existing tests pass without modification
- New tests for `CircuitOpenError -> 503` pass
- New tests for `TransientAuthError vs PermanentAuthError` pass

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `AuthSettings()` reads different env vars than `AuthConfig.from_env()` at deployment time | Medium | High (auth fails entirely) | SDK's legacy env var alias support maps `AUTH_*` to `AUTH__*` with deprecation warning. No immediate env var changes required. |
| Top-level import of `autom8y_auth` errors in `dependencies.py` causes `ImportError` when SDK not installed | Low | Medium (503 on all requests) | The `auth` optional dependency is installed in all environments that use JWT auth. Add a clear error message if import fails at startup. |
| Exception handler ordering is wrong (e.g., `AuthError` catches before `CircuitOpenError`) | Low | High (CircuitOpenError returns 401 instead of 503) | Order handlers from most specific to least specific: `CircuitOpenError` -> `TransientAuthError` -> `PermanentAuthError` -> `AuthError`. Test coverage verifies this. |
| Existing tests break due to MRO change in error hierarchy | Very Low | Low (test failures, not production) | SDK preserves all leaf error types and their `.code` attributes. `except AuthError` still catches everything. `isinstance(e, TokenExpiredError)` still works. |
| Circuit breaker opens in production and returns 503 instead of retrying | N/A (expected behavior) | N/A | This is the desired behavior per the PRD. The circuit breaker protects against cascading JWKS failures. 503 is the correct status code for a transient infrastructure issue. |

---

## 13. Attestation Table

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD (this document) | `/Users/tomtenuta/Code/autom8_asana/docs/tdd/auth-v1-migration.md` | Pending (post-write) |
| Source: jwt_validator.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/auth/jwt_validator.py` | Read |
| Source: dependencies.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | Read |
| Source: dual_mode.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/auth/dual_mode.py` | Read |
| Source: auth/__init__.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/auth/__init__.py` | Read |
| Source: pyproject.toml | `/Users/tomtenuta/Code/autom8_asana/pyproject.toml` | Read |
| Test: test_jwt_validator.py | `/Users/tomtenuta/Code/autom8_asana/tests/test_auth/test_jwt_validator.py` | Read |
| Test: test_integration.py | `/Users/tomtenuta/Code/autom8_asana/tests/test_auth/test_integration.py` | Read |
| Test: test_dependencies.py | `/Users/tomtenuta/Code/autom8_asana/tests/test_auth/test_dependencies.py` | Read |
| SDK: config.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-auth/src/autom8y_auth/config.py` | Read |
| SDK: errors.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-auth/src/autom8y_auth/errors.py` | Read |
| SDK: client.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-auth/src/autom8y_auth/client.py` | Read |
| SDK: __init__.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-auth/src/autom8y_auth/__init__.py` | Read |
| SDK: pyproject.toml | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-auth/pyproject.toml` | Read |
| Ref: SDK TDD | `/Users/tomtenuta/Code/autom8y/docs/tdd/autom8y-auth-v1-resilience.md` | Read |
| Ref: SDK PRD | `/Users/tomtenuta/Code/autom8y/docs/prd/autom8y-auth-v1-resilience.md` | Read |

---

## 14. Handoff Checklist

- [x] All 5 import sites have file-by-file transformation specs (Sections 4.1-4.5)
- [x] Dual-mode auth boundaries are explicitly documented with error scope per path (Section 2)
- [x] Lazy singleton replacement pattern is specified with code example (Section 5)
- [x] CircuitOpenError -> 503 is scoped to JWT path ONLY (Section 2.3, Section 2.4)
- [x] validate_service_token() changes (non-changes) are specified (Section 6)
- [x] AuthSettings configuration fully specified (Section 7)
- [x] Env var migration table is complete (Section 8)
- [x] pyproject.toml changes specified (Section 9)
- [x] Test transformation covers all 3 test files with new test specifications (Section 10)
- [x] Implementation sequence defined (Section 11)
- [x] Risk assessment complete (Section 12)
- [x] No ambiguous language -- every specification is concrete and actionable
