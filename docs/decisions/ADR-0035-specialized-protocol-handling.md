# ADR-0035: Specialized Protocol Handling (Webhooks & Attachments)

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0008 (Webhook Verification), ADR-0009 (Attachment Handling), ADR-0015 (Batch Request Format)
- **Related**: reference/API-INTEGRATION.md

## Context

While most Asana API operations use standard JSON request/response, certain features require specialized protocol handling:

1. **Webhooks**: HMAC-SHA256 signature verification, handshake secret exchange
2. **Attachments**: Multipart form encoding for uploads, streaming downloads for large files
3. **Batch API**: Specific request envelope format (`{"data": {"actions": [...]}}`)

Each requires different handling than standard JSON operations but should integrate cleanly with the SDK's architecture.

## Decision

### Webhook Signature Verification

**Implement as static utility methods on `WebhooksClient` with framework-agnostic design.**

```python
class WebhooksClient:
    @staticmethod
    def verify_signature(
        request_body: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Verify webhook signature using HMAC-SHA256.

        Args:
            request_body: Raw request body as bytes (before decoding)
            signature: Value from X-Hook-Signature header
            secret: Webhook secret from handshake

        Returns:
            True if signature is valid, False otherwise
        """
        expected = hmac.new(
            secret.encode('utf-8'),
            request_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def extract_handshake_secret(headers: dict[str, str]) -> str | None:
        """Extract X-Hook-Secret from handshake request headers."""
        # Case-insensitive header lookup
        for key, value in headers.items():
            if key.lower() == 'x-hook-secret':
                return value
        return None
```

**Design choices**:
- **Static methods**: No client state needed, pure functions
- **Bytes input**: Verify before decoding to avoid encoding issues
- **Boolean return**: Allows flexible error handling (not raised exceptions)
- **Timing-safe comparison**: Uses `hmac.compare_digest` to prevent timing attacks
- **No secret storage**: Consumers manage secret storage (database, secret manager, env vars)

### Attachment Multipart Handling

**Extend `AsyncHTTPClient` with multipart upload and streaming download methods.**

```python
class AsyncHTTPClient:
    async def post_multipart(
        self,
        path: str,
        *,
        file: tuple[str, BinaryIO, str],  # (filename, file_obj, content_type)
        fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload file via multipart/form-data.

        Leverages httpx's built-in multipart support.
        """
        files = {'file': file}
        data = fields or {}
        return await self.request('POST', path, files=files, data=data)

    async def download_stream(
        self,
        path: str,
        destination: BinaryIO,
        *,
        chunk_size: int = 8192,
    ) -> int:
        """Stream download to file, return bytes downloaded.

        Prevents memory exhaustion on large files.
        """
        async with self._client.stream('GET', path) as response:
            response.raise_for_status()
            total = 0
            async for chunk in response.aiter_bytes(chunk_size):
                destination.write(chunk)
                total += len(chunk)
            return total
```

**Design choices**:
- **Native httpx multipart**: Use httpx's built-in multipart encoding
- **Streaming downloads**: Use `async with response.aiter_bytes()` for memory efficiency
- **Configurable chunk size**: Default 8192 bytes, allow override
- **Return bytes count**: Enable progress tracking

### Batch API Request Format

**Wrap batch actions in required data envelope.**

```python
class BatchClient:
    async def submit_async(
        self,
        actions: list[BatchAction],
    ) -> BatchResult:
        """Submit batch request to Asana API.

        Wraps actions in required {"data": {"actions": [...]}} format.
        """
        payload = {
            "data": {
                "actions": [action.to_dict() for action in actions]
            }
        }
        response = await self._http.post('/batch', json=payload)
        return BatchResult.from_response(response)
```

**Design choice**: Centralize envelope wrapping in `BatchClient.submit_async` to ensure consistent format.

## Rationale

### Why Static Methods for Webhooks?

**Signature verification is a pure function**:
- Takes inputs (body, signature, secret)
- Returns boolean result
- No side effects, no state needed
- Can be used without instantiating full SDK

**Benefits**:
- Use without full SDK initialization
- Easier testing (no mock setup)
- Framework-agnostic (works with FastAPI, Flask, Django, etc.)
- Clear separation from API calls

**Rejected alternatives**:
- **Instance method**: Requires instantiated client for verification, unnecessary coupling
- **Middleware pattern**: Couples SDK to web frameworks, high maintenance burden
- **Raise exception on invalid**: Boolean is simpler and more flexible
- **Store secret in client**: Doesn't work with pre-existing webhooks or multiple webhooks

### Why Bytes Input for Signature Verification?

Request bodies must be verified **before decoding** to avoid character encoding issues that could affect signature. Bytes-to-bytes comparison ensures no encoding transformations interfere.

### Why Extend HTTP Client for Attachments?

**Attachment operations are HTTP operations**:
- Leverage existing rate limiting
- Leverage existing retry logic
- Leverage existing connection pooling
- No separate upload infrastructure needed

**Multipart support**: httpx provides built-in multipart encoding; we expose it cleanly.

**Streaming downloads**: Essential for large files (100MB+ attachments exist in Asana).

### Why Data Envelope for Batch API?

Asana Batch API **requires** the specific format:

```json
{
  "data": {
    "actions": [
      {"action_type": "create_task", "data": {...}},
      {"action_type": "update_task", "data": {...}}
    ]
  }
}
```

Centralizing this in `BatchClient` ensures:
- Users never construct envelope manually
- Format errors impossible
- Consistent with Asana expectations
- Single place to update if format changes

## Alternatives Considered

### Webhook Alternatives

#### Raise Exception on Invalid Signature

- **Pros**: Forces handling, matches SDK error patterns
- **Cons**: Not all consumers want exceptions, awkward conditional logic, exception overhead
- **Why not chosen**: Boolean is simpler and more flexible

#### Framework-Specific Middleware

- **Pros**: Zero-effort integration (e.g., FastAPI dependency)
- **Cons**: Couples SDK to frameworks, maintenance burden, may conflict with user middleware
- **Why not chosen**: Too opinionated; static method is framework-agnostic

### Attachment Alternatives

#### Separate AttachmentUploader Class

- **Pros**: Separation of concerns
- **Cons**: Duplicate rate limiting/retry/auth logic, another class to instantiate
- **Why not chosen**: Attachment upload is HTTP; extend HTTP client

#### In-Memory Buffer for Downloads

- **Pros**: Simpler API (return bytes)
- **Cons**: Memory exhaustion on large files, OOM risk
- **Why not chosen**: Streaming prevents memory issues

### Batch Alternatives

#### User Constructs Envelope

- **Pros**: Explicit, user sees format
- **Cons**: Easy to get wrong, brittle, poor DX
- **Why not chosen**: Centralize format in SDK

## Consequences

### Positive

**Webhooks**:
- Framework-agnostic verification
- Secure by default (timing-safe comparison)
- Simple API (one method, three parameters)
- Testable (pure function)

**Attachments**:
- Efficient memory usage (streaming)
- Reuse HTTP transport (rate limiting, retry, auth)
- Clean multipart API via httpx

**Batch**:
- Correct format guaranteed
- Users never construct envelope manually
- Single update point if format changes

### Negative

**Webhooks**:
- Consumer responsible for secret storage
- No automatic middleware integration

**Attachments**:
- Streaming requires destination file handle (not just bytes)

**Batch**:
- Abstraction hides envelope details (may confuse debugging)

### Neutral

**Webhooks**:
- Bytes requirement (consumers must provide raw bytes, not decoded string)
- Boolean return (users may want exceptions)

**Attachments**:
- Chunk size configuration needed for progress tracking

## Compliance

### Enforcement

1. **Webhook verification**:
   - [ ] Uses static method on `WebhooksClient`
   - [ ] No secret storage in client
   - [ ] Uses `hmac.compare_digest` for timing safety
   - [ ] Accepts bytes for body, not string

2. **Attachment handling**:
   - [ ] Multipart upload via `AsyncHTTPClient.post_multipart`
   - [ ] Streaming download via `AsyncHTTPClient.download_stream`
   - [ ] Chunk size configurable with sane default

3. **Batch format**:
   - [ ] All batch requests wrapped in `{"data": {"actions": [...]}}`
   - [ ] Wrapping handled by `BatchClient.submit_async`
   - [ ] Users never construct envelope manually

### Testing

- Known webhook test vectors pass verification
- Invalid signatures return False
- Multipart uploads encode correctly
- Streaming downloads handle large files without OOM
- Batch requests match Asana's expected format

### Documentation

- Clear examples for common web frameworks (FastAPI, Flask)
- Attachment upload/download examples with error handling
- Batch API usage patterns documented
