# ADR-0008: Webhook Signature Verification Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-SDK-020), [TDD-0004](../design/TDD-0004-tier2-clients.md)

## Context

Asana webhooks use signature verification to ensure webhook events are authentic. When a webhook is created, Asana:

1. Sends a handshake request with `X-Hook-Secret` header
2. The receiving server must respond with the same secret in `X-Hook-Secret` response header
3. For subsequent events, Asana includes `X-Hook-Signature` header containing HMAC-SHA256 of the request body

The SDK needs to provide a way for consumers to verify these signatures without requiring them to understand the cryptographic details.

Forces at play:
1. **Security**: Signature verification is critical to prevent spoofed events
2. **Simplicity**: Consumers shouldn't need to know HMAC-SHA256 details
3. **Flexibility**: Different web frameworks have different request handling
4. **Statelessness**: Verification shouldn't require SDK client state
5. **Performance**: Signature verification happens on every webhook event

## Decision

**The WebhooksClient SHALL provide signature verification as static utility methods** with the following design:

### 1. Static Method for Signature Verification

```python
@staticmethod
def verify_signature(
    request_body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify webhook signature using HMAC-SHA256."""
```

This is a static method because:
- No client state is needed
- Can be used without instantiating the full SDK
- Pure function with no side effects

### 2. Helper for Handshake Secret Extraction

```python
@staticmethod
def extract_handshake_secret(headers: dict[str, str]) -> str | None:
    """Extract X-Hook-Secret from handshake request headers."""
```

This helper handles case-insensitive header lookup.

### 3. Implementation Details

- Uses Python's `hmac` module with SHA256
- Uses `hmac.compare_digest` for timing-safe comparison
- Expects raw bytes for request body (not decoded string)
- Returns boolean (not raises exception) for failed verification

### 4. Secret Storage Responsibility

The SDK does NOT store webhook secrets. Consumers must:
- Capture the secret during handshake
- Store it securely (e.g., in database, secret manager)
- Pass it to `verify_signature` on each event

## Rationale

1. **Static methods**: Signature verification is a pure function - it takes inputs and returns a result without needing any SDK state. Making it static allows:
   - Use without full SDK initialization
   - Easier testing
   - Clear separation from API calls

2. **Bytes input**: Request bodies should be verified before decoding to avoid any character encoding issues that could affect the signature.

3. **Boolean return**: Returning `False` for invalid signatures (rather than raising exceptions) allows consumers to handle invalid signatures as they see fit:
   - Log and return 401
   - Silently discard
   - Queue for investigation

4. **No secret storage**: Webhook secrets are sensitive and their storage requirements vary by consumer:
   - Some use databases
   - Some use secret managers
   - Some use environment variables
   The SDK shouldn't prescribe storage strategy.

5. **HMAC-SHA256**: This is what Asana uses. We don't need to support other algorithms.

## Alternatives Considered

### Instance Method on WebhooksClient

- **Description**: `client.webhooks.verify_signature(...)` as instance method
- **Pros**: Consistent with other client methods
- **Cons**:
  - Requires instantiated client for verification
  - Unnecessary coupling to HTTP transport
  - Can't be used in webhook handler without full SDK
- **Why not chosen**: Verification has no dependency on client state

### Raise Exception on Invalid Signature

- **Description**: Raise `InvalidSignatureError` instead of returning False
- **Pros**:
  - Forces handling of invalid signatures
  - Matches error handling for other SDK operations
- **Cons**:
  - Not all consumers want exceptions
  - Makes conditional logic awkward
  - Exception overhead for common case (malicious requests)
- **Why not chosen**: Boolean is simpler and more flexible

### Middleware Pattern

- **Description**: Provide framework-specific middleware (FastAPI, Flask, etc.)
- **Pros**: Zero-effort integration
- **Cons**:
  - Couples SDK to web frameworks
  - Maintenance burden for multiple frameworks
  - May conflict with consumer's middleware
- **Why not chosen**: Too opinionated; static method is framework-agnostic

### Store Secret in Client

- **Description**: Store webhook secret in WebhooksClient after create
- **Pros**: Convenient for single-webhook scenarios
- **Cons**:
  - Doesn't work with pre-existing webhooks
  - What about multiple webhooks?
  - Security risk if client is logged/serialized
- **Why not chosen**: Secret storage is consumer responsibility

## Consequences

### Positive
- **Framework agnostic**: Works with any web framework
- **Secure by default**: Uses timing-safe comparison
- **Simple API**: One method, three parameters
- **Testable**: Pure function, easy to unit test

### Negative
- **Consumer responsibility**: Must store and manage secrets
- **Manual integration**: No automatic middleware

### Neutral
- **Bytes requirement**: Consumers must provide raw bytes, not decoded string

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - [ ] Signature verification uses static method
   - [ ] No secret storage in client
   - [ ] Uses hmac.compare_digest

2. **Tests verify**:
   - Known test vectors pass
   - Timing-safe comparison is used
   - Invalid signatures return False

3. **Documentation**: Clear examples for common frameworks (FastAPI, Flask)
