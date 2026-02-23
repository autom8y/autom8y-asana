# SCOUT-jwt-auth-consolidation

**Date**: 2026-02-23
**Analyst**: technology-scout
**Classification**: Necessity (defensive -- split trust domain is a security debt item)
**Complexity**: EVALUATION

---

## Executive Summary

The autom8y ecosystem operates two independent JWT trust domains: the modern platform (RS256, JWKS, `autom8y-auth` SDK) and the legacy monolith (HS256, local secret key). This assessment evaluates five proven approaches for consolidating into a single trust domain. **Verdict: Adopt Dual-Validation Middleware (Approach 1) as the primary migration pattern, with ALB JWT Verification (Approach 3) as a hardening overlay once the legacy monolith issues RS256 tokens.** The other approaches are rated Hold or Avoid for this context. Token Exchange (Approach 2) is rated Assess -- worth investigating if the legacy monolith cannot be modified at all, but adds architectural complexity that Approach 1 avoids.

---

## Technology Overview

| Attribute | Value |
|-----------|-------|
| **Category** | Authentication / Migration Pattern |
| **Problem** | Split trust domain between HS256 (legacy) and RS256 (platform) |
| **Urgency** | Medium -- no active incident, but blocks cross-service trust and creates audit gap |
| **Constraint** | 2-3 engineers, 6-month runway, legacy monolith has ~80 deps and 1921-line main.py |

### Current Architecture

```
                    RS256 Trust Zone                    HS256 Trust Zone
                    +-----------------+                 +------------------+
                    | auth service    |                 | autom8 (legacy)  |
                    | (ECS Fargate)   |                 | (Lambda behind   |
                    |                 |                 |  ALB)            |
                    | Issues RS256    |                 | Issues HS256     |
                    | JWKS at         |                 | Local secret key |
                    | /.well-known/   |                 | python-jose      |
                    | jwks.json       |                 | (unmaintained)   |
                    +--------+--------+                 +--------+---------+
                             |                                   |
           +-----------------+---------+                         |
           |                 |         |                         |
    +------+------+  +------+------+  +------+------+           |
    | autom8y-    |  | autom8y-    |  | autom8y-    |           |
    | asana       |  | data        |  | ads         |           |
    | (validates  |  | (validates  |  | (validates  |           |
    |  via SDK)   |  |  via SDK)   |  |  via SDK)   |           |
    +-------------+  +-------------+  +-------------+           |
                                                                |
                                               NO CROSS-TRUST POSSIBLE
```

---

## Approach-by-Approach Assessment

---

### Approach 1: Dual-Validation Middleware

**Description**: The legacy monolith accepts both HS256 tokens (current keys) and RS256 tokens (from auth service JWKS) during a migration window. Middleware inspects the JWT `alg` header and routes to the appropriate validation path.

#### Maturity: Mainstream

This is the standard approach for JWT algorithm migration. Every major identity platform (Auth0, Keycloak, Okta) documents dual-algorithm validation as the canonical migration path.

#### Production References

- **Auth0**: Documents RS256-to-HS256 coexistence in their [migration guides](https://auth0.com/blog/rs256-vs-hs256-whats-the-difference/)
- **Keycloak 26.x**: Supports multiple active signing algorithms simultaneously
- **PyJWT 2.11.0**: Explicitly supports `algorithms=["RS256", "HS256"]` parameter -- the library validates that the token's `alg` header matches one of the allowed list
- **FastAPI/Starlette ecosystem**: `autom8y_auth.middleware.JWTAuthMiddleware` already demonstrates the pattern in production (see `/Users/tomtenuta/Code/autom8y-asana/.venv/lib/python3.12/site-packages/autom8y_auth/middleware.py`)

#### Python Ecosystem Fit

| Library | Status | Dual-Algo Support | Notes |
|---------|--------|-------------------|-------|
| **PyJWT 2.11.0** | Actively maintained, 10K+ GitHub stars | YES -- `algorithms=["RS256","HS256"]` | FastAPI docs now recommend PyJWT over python-jose |
| **python-jose 3.5.0** | Unmaintained since 2021, security CVEs | YES -- but deprecated | autom8y-auth SDK already uses python-jose internally; autom8-core uses it in legacy |
| **authlib 1.6.6** | Actively maintained | YES | Heavier dependency, better for full OIDC |

**Critical observation**: The `autom8y-auth` SDK (`AuthClient._validate_with_jwks()` at line 303-386 of `client.py`) hardcodes `algorithms=list(self._settings.algorithms)` which defaults to `("RS256",)`. The SDK does NOT support HS256 validation -- it requires JWKS-based key lookup by `kid`. This means dual-validation in the legacy monolith would use PyJWT directly (or python-jose, already a dependency) rather than the `autom8y-auth` SDK.

#### Risk Profile

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Algorithm confusion attack (HS256 key used as RS256 public key) | Low | Critical | Explicitly whitelist algorithms per key; NEVER derive algorithm from JWT header alone |
| Widened attack surface during coexistence | Medium | Medium | Time-box migration window (60-90 days max); deprecate HS256 path with metric counter |
| Legacy HS256 secret key leaked | Low | High | Already a risk today; unchanged by this approach |
| python-jose in legacy has unpatched CVEs | Medium | Medium | Migration to PyJWT is independent of this approach but should be sequenced |

#### Estimated Calendar Time

- **Implementation**: 2-3 weeks (add RS256 validation path to legacy `main.py`, fetch JWKS, validate with `kid` lookup)
- **Testing**: 1 week (dual-mode tests, algorithm confusion regression tests)
- **Migration window**: 60-90 days (callers switch from HS256 to RS256 tokens)
- **Cleanup**: 1 week (remove HS256 path after all callers migrated)
- **Total**: ~2-4 months including migration window

#### Requires Legacy Monolith Changes

**YES** -- this is the core of the approach. Changes to `app/main.py` auth middleware to add RS256 validation path alongside existing HS256.

---

### Approach 2: Token Exchange (RFC 8693)

**Description**: The auth service accepts HS256 tokens from the legacy monolith and issues RS256 tokens in exchange. Downstream services only see RS256 tokens. The legacy monolith continues issuing HS256 unchanged.

#### Maturity: Growing (standardized, but custom implementation needed)

RFC 8693 was published in 2020. Keycloak 26.2 added full standard token exchange in May 2025. Auth0 supports custom token exchange. However, no off-the-shelf Python library implements RFC 8693 server-side -- you would build a custom endpoint in the auth service.

#### Production References

- **Keycloak 26.2**: [Standard Token Exchange V2](https://www.keycloak.org/2025/05/standard-token-exchange-kc-26-2) (GA, fully supported)
- **Auth0**: [Custom Token Exchange](https://auth0.com/docs/authenticate/custom-token-exchange) (production feature)
- **Authlete 2.3+**: RFC 8693 compliant
- **Custom implementations**: Microsoft Azure AD, Salesforce, Box all use token exchange in production

#### Python Ecosystem Fit

| Component | Library | Status |
|-----------|---------|--------|
| Token exchange endpoint | Custom FastAPI route in auth service | Must build; no off-the-shelf Python RFC 8693 server |
| HS256 verification | python-jose / PyJWT | Both support HS256 validation |
| RS256 issuance | Already exists in auth service | Reuse existing token minting |
| Client-side exchange | httpx call to auth service | Simple HTTP POST |

#### Risk Profile

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Auth service becomes SPOF for ALL legacy requests | High | High | Circuit breaker, caching exchanged tokens |
| Latency: every legacy-originated request adds auth service RTT | High | Medium | Cache exchanged RS256 tokens (honor `exp` from original HS256) |
| Auth service must validate HS256 tokens (needs shared secret) | Certain | Medium | Auth service becomes coupled to legacy secret management |
| Complexity: new endpoint, new protocol, new failure mode | Medium | Medium | Time-box implementation spike |
| Token replay: exchanged token could be replayed | Low | Medium | Short-lived exchanged tokens, `jti` uniqueness |

#### Estimated Calendar Time

- **Auth service changes**: 2-3 weeks (new `/internal/token-exchange` endpoint, HS256 validation, RS256 minting)
- **Legacy integration**: 1 week (add token exchange call before downstream requests)
- **Testing**: 2 weeks (exchange flow, failure modes, caching, replay protection)
- **Total**: ~5-7 weeks

#### Requires Legacy Monolith Changes

**MINIMAL** -- only if you want callers TO the legacy monolith to use RS256 (then the monolith needs RS256 validation anyway, which is Approach 1). If the goal is only that calls FROM the legacy monolith to satellite services use RS256, then the legacy monolith adds a token exchange call before outbound requests. This is a smaller change (~50 lines), but it only solves unidirectional trust.

---

### Approach 3: Reverse Proxy / ALB JWT Verification

**Description**: AWS ALB or API Gateway validates JWT before requests hit the legacy service. Verified claims are injected as headers. The legacy service trusts the gateway.

#### Maturity: Mainstream (for RS256); Not Applicable (for HS256)

AWS ALB JWT Verification launched November 2025. However, **ALB JWT verification does NOT support HS256** -- it only supports asymmetric algorithms (RS256, RS384, RS512, ES256, ES384, ES512, Ed25519, Ed448) via JWKS endpoints.

This means Approach 3 cannot validate the legacy monolith's existing HS256 tokens. It can only work AFTER the monolith's callers switch to RS256 tokens (which requires Approach 1 or Approach 4 first).

#### Production References

- **AWS ALB**: [JWT Verification](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-verify-jwt.html) -- GA in all regions since November 2025
- **API Gateway**: [JWT Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html) -- RS256 only, production-ready
- **AWS JWT Verify library**: [awslabs/aws-jwt-verify](https://github.com/awslabs/aws-jwt-verify) -- RS256, RS384, RS512, ES256, ES384, ES512, Ed25519, Ed448

#### Python Ecosystem Fit

No Python code changes needed for the JWT validation itself -- ALB handles it. The legacy monolith would read verified claims from `x-amzn-jwt-*` headers instead of validating JWTs itself. However, this creates a hard dependency on the ALB path -- direct-to-service calls (e.g., in development or from Lambda) bypass the ALB.

#### Risk Profile

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ALB only supports asymmetric algorithms -- HS256 NOT supported | Certain | Blocking | Must complete HS256-to-RS256 migration FIRST |
| Header injection: if legacy service trusts headers without verifying source | Medium | Critical | Restrict to ALB-originated requests only (check `x-forwarded-for` or use VPC security groups) |
| JWKS endpoint availability at request time | Low | Medium | ALB fails open or closed depending on config; auth service is ECS Fargate with health checks |
| Development/testing bypass: no ALB in local dev | Medium | Low | Keep application-level JWT validation as fallback |

#### Estimated Calendar Time

- **Terraform ALB configuration**: 1-2 days
- **Legacy service header-reading**: 2-3 days
- **Prerequisite**: Approach 1 or 4 must be completed first (HS256-to-RS256 migration)
- **Total as standalone**: Not viable. As overlay after RS256 migration: 1 week.

#### Requires Legacy Monolith Changes

**YES** -- but minimal. Replace JWT validation with header reading. However, this only works after HS256 tokens are eliminated.

---

### Approach 4: Big-Bang Cutover

**Description**: Replace HS256 signing in the legacy monolith with RS256 signing via `autom8y-auth` SDK calls in a single deployment. All callers must update simultaneously.

#### Maturity: N/A (deployment pattern, not a technology)

This is a migration strategy, not a technology choice. The underlying technology (RS256 + JWKS) is fully mature.

#### Production References

Big-bang migrations are widely documented as anti-patterns for authentication systems. Notable failures include:

- GitHub's 2023 RSA SSH key rotation required advance notice and staged rollout
- Any OIDC provider key rotation follows staged rollout, not big-bang

#### Python Ecosystem Fit

The `autom8y-auth` SDK (`AuthClient` + `AuthSettings`) is already production-ready. The legacy monolith would import the SDK (already has `autom8y-core>=0.2.0,<1.0.0` from CodeArtifact). The SDK would handle token issuance if the auth service's `/internal/s2s/token` endpoint is used, or the monolith would sign RS256 tokens directly using private keys from the auth service.

However, the legacy monolith is constrained to Python >=3.10,<3.12 while `autom8y-auth` requires Python >=3.11. This is compatible but narrows the version range.

#### Risk Profile

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| All callers must update tokens simultaneously | High | Critical | Coordinate deployment across all consumers; any missed caller is locked out |
| Rollback requires re-deploying ALL services | High | Critical | Feature flag would help but adds complexity defeating the "big-bang" premise |
| Legacy monolith's 80 dependencies may conflict with autom8y-auth SDK | Medium | High | Test in CI first; autom8y-auth has minimal transitive deps |
| Service disruption during deployment window | Medium | High | Blue-green deploy; but token incompatibility spans the fleet, not just one service |

#### Estimated Calendar Time

- **Implementation**: 1-2 weeks
- **Coordination**: 2-4 weeks (aligning all callers)
- **Deployment**: 1 day (the "bang")
- **Total**: ~3-6 weeks, but with significant coordination overhead

#### Requires Legacy Monolith Changes

**YES** -- significant. Replace auth module, token signing, secret management. Deploy new SDK dependency. Test all 30+ API integrations.

---

### Approach 5: OIDC/OAuth2 Standard Adoption

**Description**: Move both systems to a standard OIDC provider, either using the existing auth service as an OIDC provider or adopting Authlib/Keycloak.

#### Maturity: Mainstream (for OIDC); Overkill (for this problem)

OIDC is a fully mature standard. Authlib 1.6.6 can build OIDC providers in Python. However, the autom8y auth service already issues RS256 JWTs with JWKS -- it is functionally an OIDC-like provider without the full OIDC discovery/authorization code flow. Adding full OIDC compliance addresses a different problem (user-facing OAuth flows, third-party integrations) rather than the S2S trust consolidation at hand.

#### Production References

- **Authlib**: [OIDC Provider](https://docs.authlib.org/en/latest/specs/oidc.html) -- production-ready, Flask and Django support
- **Keycloak**: Full OIDC provider, but introduces a new external dependency (Java, requires dedicated infrastructure)
- **Auth0/Okta**: Managed OIDC, but would replace the existing auth service

#### Python Ecosystem Fit

Authlib 1.6.6 is well-maintained (4K+ GitHub stars) and supports building custom OIDC providers in FastAPI. However, adopting it would mean:

1. Adding OIDC discovery (`.well-known/openid-configuration`) to the auth service
2. Implementing authorization code flow, token endpoint, userinfo endpoint
3. Migrating all services from custom JWT validation to OIDC client libraries
4. Significant scope expansion beyond the consolidation goal

#### Risk Profile

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep: OIDC adoption becomes a multi-quarter project | High | High | Resist; solve the immediate problem first |
| Overengineering: S2S auth does not need OIDC flows | Certain | Medium | OIDC is for user auth flows; S2S uses client credentials |
| Migration of all services to new auth patterns | High | High | Every satellite service needs changes |
| Keycloak/external provider introduces operational burden | Medium | Medium | Stay with custom auth service |

#### Estimated Calendar Time

- **Auth service OIDC additions**: 4-8 weeks
- **All service migrations**: 4-8 weeks
- **Legacy monolith migration**: 2-4 weeks
- **Total**: 3-6 months (fills entire runway with no guarantee of completion)

#### Requires Legacy Monolith Changes

**YES** -- the entire point is to change how every service authenticates.

---

## Comparison Matrix

| Criteria | Status Quo (split domains) | Approach 1: Dual-Validation | Approach 2: Token Exchange | Approach 3: ALB JWT Verify | Approach 4: Big-Bang | Approach 5: OIDC |
|----------|---------------------------|---------------------------|---------------------------|---------------------------|---------------------|-------------------|
| **Maturity** | N/A | Mainstream | Growing | Mainstream (RS256 only) | N/A | Mainstream |
| **Migration risk** | Ongoing debt | Low (gradual) | Medium (new SPOF) | Low (overlay) | High (all-at-once) | High (scope) |
| **Legacy code changes** | None | Moderate (~200 LOC) | Minimal (outbound) | Minimal (headers) | Significant (~500 LOC) | Significant |
| **Auth service changes** | None | None | Moderate (new endpoint) | None | None | Significant |
| **Calendar time** | N/A | 2-4 months | 5-7 weeks | 1 week (after RS256 migration) | 3-6 weeks | 3-6 months |
| **HS256 coexistence** | Permanent | Time-boxed (60-90 days) | Permanent (exchange hides it) | Not supported | Eliminated immediately | Eliminated eventually |
| **Rollback safety** | N/A | Remove RS256 path | Revert exchange endpoint | Remove ALB rule | Redeploy all services | Revert everything |
| **python-jose dependency** | Required (both sides) | Required during migration | Required (legacy + auth svc) | Required (legacy only) | Replaced | Replaced |
| **Solves bidirectional trust** | No | Yes | Partial (outbound only) | Yes (after migration) | Yes | Yes |
| **Team skill match** | N/A | High (PyJWT/JWKS known) | Medium (new protocol) | High (Terraform/ALB known) | High | Low (OIDC spec) |

---

## Fit Assessment

### Philosophy Alignment

The autom8y platform already has the right target architecture: RS256 JWTs, JWKS endpoint, SDK-based validation. The problem is not "what should we use" but "how do we get the legacy monolith into the existing trust zone." Approach 1 (Dual-Validation) aligns with the platform's existing philosophy of gradual migration (see: auth-mysql-sync, D-002 calendar-gated v1 router removal, ADR-011 legacy preload fallback pattern).

### Stack Compatibility

- **autom8y-auth SDK**: Already in production across all satellite services. RS256 validation is battle-tested.
- **python-jose 3.5.0**: Already a dependency of both the legacy monolith (via `autom8-core.auth`) and the `autom8y-auth` SDK. Unmaintained but functional.
- **PyJWT 2.11.0**: Recommended replacement for python-jose. FastAPI docs updated to recommend it. Migration is orthogonal to this assessment but should be planned.
- **ALB JWT Verification**: Available in production AWS environment. Terraform modules already exist for ALB configuration.

### Team Readiness

- The team has already built dual-mode auth in autom8y-asana (`detect_token_type()`, `AuthMode.JWT`/`AuthMode.PAT`, `get_auth_context()`). The pattern is proven.
- The auth-v1 migration TDD at `/Users/tomtenuta/Code/autom8y-asana/docs/tdd/auth-v1-migration.md` demonstrates deep familiarity with the SDK error hierarchy and validation flow.
- The ecosystem topology inventory documents the exact trust boundary (Section 4.2 Authentication Topology).

---

## Recommendation

### Approach 1: Dual-Validation Middleware -- **ADOPT**

**Rationale**: Lowest risk, proven pattern, aligns with existing migration culture (gradual, reversible, time-boxed). The autom8y-asana codebase already implements an analogous dual-mode pattern (`AuthMode.JWT` vs `AuthMode.PAT`). The legacy monolith adds RS256 validation alongside existing HS256, callers migrate over 60-90 days, then HS256 is removed.

**Confidence**: High. The pattern is well-understood, the libraries are available, and the team has demonstrated proficiency with dual-mode auth.

### Approach 2: Token Exchange -- **ASSESS**

**Rationale**: Worth investigating IF the legacy monolith cannot be modified (e.g., code freeze, political resistance). Token exchange solves outbound trust without touching legacy auth code. However, it adds a new SPOF, a new protocol, and does not solve inbound trust to the legacy monolith. **Recommend a 2-day spike** to prototype the auth service exchange endpoint before committing.

**Confidence**: Medium. RFC 8693 is standard, but custom implementation introduces risk.

### Approach 3: ALB JWT Verification -- **HOLD (adopt as Phase 2 overlay)**

**Rationale**: Excellent defense-in-depth once all services are on RS256, but cannot solve the HS256 problem directly. Plan this as a Phase 2 hardening step after Approach 1 completes.

**Confidence**: High for the technology. Not applicable as a standalone solution.

### Approach 4: Big-Bang Cutover -- **AVOID**

**Rationale**: Violates the team's demonstrated migration philosophy (gradual, reversible, time-boxed). Introduces unnecessary coordination risk across all services. The benefit (no coexistence period) does not justify the blast radius of a failed deployment.

**Confidence**: High (in the avoidance recommendation).

### Approach 5: OIDC Standard Adoption -- **HOLD**

**Rationale**: Correct strategic direction for eventual user-facing OAuth flows, but massively overscoped for the S2S trust consolidation problem. The auth service's current JWT+JWKS architecture is functionally equivalent to OIDC for S2S. Revisit when user-facing OAuth or third-party integrations require it.

**Confidence**: High.

---

## Recommended Implementation Sequence

```
Phase 1: Dual-Validation (Approach 1)         Phase 2: Hardening
[Weeks 1-4]                                    [Weeks 12-14]
+------------------------------------------+   +-------------------------+
| 1. Add RS256 validation to legacy        |   | 1. ALB JWT Verify rule  |
|    monolith alongside HS256              |   |    (Terraform)          |
| 2. Fetch JWKS from auth service          |   | 2. Remove HS256 from    |
| 3. Route by alg header                   |   |    legacy monolith      |
| 4. Deploy with HS256_DEPRECATION metric  |   | 3. Rotate HS256 secret  |
+------------------------------------------+   |    key (invalidate)     |
                |                               +-------------------------+
                v
Phase 1b: Caller Migration
[Weeks 4-12]
+------------------------------------------+
| 1. Update callers to use RS256 tokens    |
|    (acquire from auth /internal/s2s/     |
|    token endpoint)                       |
| 2. Monitor HS256_DEPRECATION counter     |
| 3. Taper HS256 usage to zero            |
+------------------------------------------+
```

---

## Key Risks and Mitigations (Selected Approach)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Algorithm confusion attack during dual-validation | Low | Critical | Explicitly map `alg` header to key type; never use HS256 secret as RS256 public key. Test with algorithm-confusion payload in CI. |
| python-jose CVE during migration window | Medium | Medium | Time-box to 90 days max. Plan python-jose-to-PyJWT migration as follow-up. The `autom8y-auth` SDK also uses python-jose -- coordinate SDK update. |
| JWKS fetch failure in legacy monolith | Low | High | Implement stale-cache fallback (cache JWKS in-process with 5-minute TTL, serve stale for 5 additional minutes -- same pattern as `autom8y-auth` SDK's `CacheSettings`). |
| Legacy monolith deployment disrupts HS256 path | Low | High | Feature flag: `ACCEPT_RS256=true/false`. Deploy with RS256 disabled, then enable via env var after smoke test. |

---

## The Acid Test

*"If we don't adopt this now, will we regret it in two years?"*

**Yes.** The split trust domain blocks:
1. Cross-service audit trails (cannot correlate JWT subjects across trust zones)
2. Security posture improvements (HS256 is symmetric -- secret sharing is inherently riskier than RS256 asymmetric)
3. python-jose deprecation (the library is unmaintained; the longer both zones depend on it, the higher the CVE exposure)
4. ALB-level JWT enforcement (cannot use AWS native JWT verification until HS256 is eliminated)

However, this is not urgent enough to justify Approach 4 (Big-Bang). The gradual approach (Approach 1) delivers the same outcome with far lower risk.

---

## Handoff

**Next step**: If Approach 1 is approved, route to **Integration Researcher** for:
- Dependency mapping of the legacy monolith's auth module
- JWKS client integration requirements (httpx vs requests vs urllib3)
- Feature flag design for `ACCEPT_RS256`
- Caller inventory (which services send HS256 tokens to the legacy monolith)
- python-jose-to-PyJWT migration sequencing

---

## Sources

- [RFC 8693 - OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693)
- [Keycloak 26.2 Standard Token Exchange](https://www.keycloak.org/2025/05/standard-token-exchange-kc-26-2)
- [Auth0 Custom Token Exchange](https://auth0.com/docs/authenticate/custom-token-exchange)
- [Auth0: RS256 vs HS256](https://auth0.com/blog/rs256-vs-hs256-whats-the-difference/)
- [SuperTokens: RS256 vs HS256](https://supertokens.com/blog/rs256-vs-hs256)
- [PyJWT 2.11.0 Digital Signature Algorithms](https://pyjwt.readthedocs.io/en/stable/algorithms.html)
- [python-jose maintenance status (GitHub issue #340)](https://github.com/mpdavis/python-jose/issues/340)
- [FastAPI python-jose deprecation discussion](https://github.com/fastapi/fastapi/discussions/9587)
- [PyJWT migration guide for python-jose users (GitHub issue #942)](https://github.com/jpadilla/pyjwt/issues/942)
- [AWS ALB JWT Verification](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-verify-jwt.html)
- [AWS ALB JWT Verification announcement (Nov 2025)](https://aws.amazon.com/about-aws/whats-new/2025/11/application-load-balancer-jwt-verification/)
- [API Gateway JWT Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html)
- [Authlib OIDC Provider](https://docs.authlib.org/en/latest/specs/oidc.html)
- [Curity: Token Exchange in OAuth](https://curity.medium.com/token-exchange-in-oauth-why-and-how-to-implement-it-a7407367cb55)
- [APIsec: JWT Security Vulnerabilities Prevention](https://www.apisec.ai/blog/jwt-security-vulnerabilities-prevention)
