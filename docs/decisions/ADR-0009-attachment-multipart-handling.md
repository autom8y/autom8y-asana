# ADR-0009: Attachment Multipart/Form-Data Handling

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-SDK-023), [TDD-0004](../design/TDD-0004-tier2-clients.md)

## Context

Asana's attachment API requires file uploads to use `multipart/form-data` encoding. This is different from all other Asana API endpoints which use `application/json`.

The current `AsyncHTTPClient` only supports JSON payloads. We need to decide how to extend it for file uploads.

Forces at play:
1. **Memory efficiency**: Large files shouldn't be loaded entirely into memory
2. **API consistency**: Upload should feel like other SDK operations
3. **Flexibility**: Support both file objects and paths
4. **Simplicity**: Don't over-engineer for one endpoint
5. **Downloads**: Attachments also need streaming download support

## Decision

**The SDK SHALL handle attachments with the following approach:**

### 1. Extend AsyncHTTPClient with Multipart Support

Add a method to `AsyncHTTPClient` for multipart uploads:

```python
async def post_multipart(
    self,
    path: str,
    *,
    files: dict[str, tuple[str, BinaryIO, str | None]],
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST with multipart/form-data encoding.

    Args:
        path: API path
        files: Dict of {field_name: (filename, file_obj, content_type)}
        data: Additional form fields

    Returns:
        Parsed JSON response
    """
```

### 2. AttachmentsClient Upload Methods

```python
async def upload_async(
    self,
    *,
    parent: str,
    file: BinaryIO,
    name: str,
    raw: bool = False,
) -> Attachment | dict[str, Any]:
    """Upload from file object."""

async def upload_from_path_async(
    self,
    *,
    parent: str,
    path: Path | str,
    name: str | None = None,
    raw: bool = False,
) -> Attachment | dict[str, Any]:
    """Upload from filesystem path (convenience)."""
```

### 3. Streaming Download Support

Add streaming response method to `AsyncHTTPClient`:

```python
async def get_stream(
    self,
    url: str,
) -> AsyncIterator[bytes]:
    """Stream response bytes for large downloads."""
```

### 4. External Attachment Support

Separate method for URL-based attachments (no file upload):

```python
async def create_external_async(
    self,
    *,
    parent: str,
    url: str,
    name: str,
    raw: bool = False,
) -> Attachment | dict[str, Any]:
    """Create attachment from external URL."""
```

### 5. Implementation Using httpx

Use httpx's built-in multipart support:

```python
# In AsyncHTTPClient
async def post_multipart(
    self,
    path: str,
    *,
    files: dict[str, tuple[str, BinaryIO, str | None]],
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = self._build_url(path)
    response = await self._client.post(
        url,
        files=files,
        data=data,
        headers=self._auth_headers(),
    )
    # Note: No "data" wrapper in response for multipart
    return self._handle_response(response)
```

## Rationale

1. **Extend AsyncHTTPClient**: Keeps all HTTP logic in one place. The `post_multipart` method is similar to `post` but with different encoding.

2. **File object interface**: Using `BinaryIO` (file-like objects) allows:
   - Reading from actual files
   - Reading from BytesIO for tests
   - Reading from any file-like object

3. **Convenience path method**: `upload_from_path_async` handles the common case of uploading from a filesystem path, avoiding boilerplate file handling.

4. **Separate external method**: External attachments (URL links) don't involve file upload and have different semantics, justifying a separate method.

5. **Streaming downloads**: Large attachments shouldn't be loaded into memory. httpx's streaming response support handles this efficiently.

6. **httpx multipart support**: httpx handles multipart encoding, boundaries, and streaming automatically. No need to manually implement RFC 2046.

## Alternatives Considered

### Custom Multipart Encoder

- **Description**: Implement multipart encoding ourselves
- **Pros**: Full control over encoding
- **Cons**:
  - Reinventing the wheel
  - Edge cases (binary data, unicode filenames)
  - Maintenance burden
- **Why not chosen**: httpx does this correctly already

### Separate File Upload Client

- **Description**: Create `FileUploadClient` distinct from `AttachmentsClient`
- **Pros**: Separation of concerns
- **Cons**:
  - Confusing API (which client to use?)
  - Inconsistent with other resources
- **Why not chosen**: Attachments should be managed by AttachmentsClient

### Load File Entirely Into Memory

- **Description**: Read file contents into bytes before upload
- **Pros**: Simpler implementation
- **Cons**:
  - Memory issues with large files
  - Unnecessary for streaming-capable httpx
- **Why not chosen**: Streaming is better for large files

### Only Support Path-Based Upload

- **Description**: Only `upload_from_path`, no file object support
- **Pros**: Simpler API
- **Cons**:
  - Can't upload from memory (e.g., generated content)
  - Less flexible for testing
- **Why not chosen**: File object support is more fundamental

### Single Upload Method with Union Type

- **Description**: `upload_async(source: BinaryIO | Path | str)`
- **Pros**: Fewer methods
- **Cons**:
  - Type checking complexity
  - Unclear semantics (is string a path or content?)
  - Harder to document
- **Why not chosen**: Explicit methods are clearer

## Consequences

### Positive
- **Memory efficient**: Streaming for large files
- **Flexible**: Both file objects and paths supported
- **Consistent**: Uses httpx's battle-tested multipart handling
- **Clean API**: Clear distinction between file and external attachments

### Negative
- **Transport layer change**: AsyncHTTPClient needs new methods
- **Two upload methods**: Could be seen as redundant

### Neutral
- **BinaryIO requirement**: Callers must provide binary mode file objects

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - [ ] File uploads use `post_multipart`
   - [ ] Downloads use streaming
   - [ ] No full-file-in-memory for large files

2. **Tests verify**:
   - Small file upload works
   - Large file upload doesn't OOM
   - Streaming download works

3. **Implementation notes**:
   - Use `httpx.AsyncClient.post(files=...)` for upload
   - Use `async with response.aiter_bytes()` for download
   - Set appropriate Content-Type if known (or let httpx detect)
