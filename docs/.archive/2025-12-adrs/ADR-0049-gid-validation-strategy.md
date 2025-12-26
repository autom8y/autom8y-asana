# ADR-0049: GID Validation Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0009 (FR-VAL-001, FR-TEST-003, FR-TEST-004), TDD-0014

## Context

The SDK accepts GID (Global ID) strings for entity identification. Invalid GIDs can cause confusing errors deep in the API call stack or create cache key collisions.

**Current State:**
- GIDs are passed through without validation
- Invalid GIDs cause errors at API call time
- Empty strings cause KeyError in tracker
- Malformed GIDs may create hash collisions

**Forces at play:**

1. **Fail-Fast**: Catch errors early, not at API call time
2. **Clear Errors**: Provide actionable error messages
3. **Security**: Prevent injection via malformed GIDs
4. **Flexibility**: Allow temporary GIDs for new entities
5. **Performance**: Validation overhead must be minimal

**Problem**: When and how should GID format be validated?

## Decision

Validate GID format **at track() time** using a regex pattern that matches both Asana GIDs and temporary GIDs.

**Pattern:**
```python
GID_PATTERN = re.compile(r"^(temp_\d+|\d+)$")
```

**Validation Logic:**
```python
def _validate_gid_format(self, gid: str | None) -> None:
    if gid is None:
        return  # New entities have no GID
    if gid == "":
        raise ValidationError("GID cannot be empty string. Use None for new entities.")
    if not GID_PATTERN.match(gid):
        raise ValidationError(
            f"Invalid GID format: {gid!r}. "
            f"GID must be a numeric string or temp_<number> for new entities."
        )
```

**Location:** `ChangeTracker.track()` method in `persistence/tracker.py`

**Valid GIDs:**
- `"1234567890"` (numeric Asana GID)
- `"temp_1"` (temporary GID for new entity)
- `None` (new entity, GID assigned by API)

**Invalid GIDs:**
- `""` (empty string)
- `"not-a-gid"` (non-numeric)
- `"12345abc"` (alphanumeric mix)
- `"; DROP TABLE"` (injection attempt)

## Rationale

### Why Validate at track() Time

1. **Earliest Entry Point**: track() is where entities enter the persistence layer
2. **Single Location**: Centralized validation in one place
3. **Fail-Fast**: User sees error immediately, not after queuing operations
4. **Before Side Effects**: No actions queued for invalid entities

Alternative (validate at commit) was rejected because:
- Error occurs later, harder to trace
- Operations may have been queued
- User has to backtrack to find cause

Alternative (validate at API call) was rejected because:
- Wasted rate limit tokens
- Error context lost
- No local validation benefit

### Why Allow None

New entities don't have GIDs yet:
```python
task = Task(name="New Task", gid=None)
session.track(task)  # Valid - gid assigned after API create
```

None is distinct from empty string:
- `None` = "no GID assigned yet"
- `""` = "someone passed empty string" (likely bug)

### Why temp_\d+ Pattern

The SDK uses temporary GIDs for dependency resolution:
```python
new_task = Task(name="New Task", gid=None)
session.track(new_task)
# Internally assigned: gid = "temp_1"
# After API create: gid = "1234567890"
```

Pattern `temp_\d+` matches these internal assignments.

### Why Regex Validation

1. **Fast**: Compiled regex is O(n) where n is GID length
2. **Clear**: Pattern is self-documenting
3. **Secure**: Rejects injection attempts
4. **Extensible**: Pattern can be updated if Asana GID format changes

### Why Raise ValidationError

New exception type provides:
1. **Clear Type**: Distinct from API errors
2. **Actionable Message**: Tells user what's wrong
3. **Catchable**: User can handle validation errors specifically

## Alternatives Considered

### Alternative 1: No Validation (Current State)

- **Description**: Accept any string, let API reject invalid
- **Pros**: Zero overhead, flexibility
- **Cons**:
  - Confusing errors deep in stack
  - Hash collisions possible
  - Injection risk
  - Empty string causes KeyError
- **Why not chosen**: Fails-late with unclear errors

### Alternative 2: Validate at Commit Time

- **Description**: Validate all GIDs just before commit
- **Pros**: Batch validation, single check point
- **Cons**:
  - Error occurs after user has queued operations
  - Harder to trace back to source
  - Wasted work building operation graph
- **Why not chosen**: track() is earlier, better UX

### Alternative 3: Validate at Each Operation

- **Description**: Validate GID every time it's used (add_tag, etc.)
- **Pros**: Defense in depth
- **Cons**:
  - Redundant validation
  - Performance overhead
  - Complex implementation
- **Why not chosen**: track() is sufficient for entry point

### Alternative 4: Stricter Pattern (Numeric Only)

- **Description**: Only allow `^\d+$`, reject temp GIDs
- **Pros**: Simpler pattern
- **Cons**:
  - Breaks internal temp GID mechanism
  - User must handle new entity GIDs differently
- **Why not chosen**: temp GIDs are essential for dependency resolution

### Alternative 5: Looser Pattern (Any Non-Empty)

- **Description**: Allow any non-empty string
- **Pros**: Maximum flexibility
- **Cons**:
  - No injection protection
  - No format guarantee
  - Hash collision still possible
- **Why not chosen**: No benefit over current state

## Consequences

### Positive
- Fail-fast on invalid GIDs
- Clear error messages with fix guidance
- Injection prevention
- Empty string bug detection
- Single validation point

### Negative
- Small performance overhead at track()
- New ValidationError exception type
- Could reject future Asana GID formats (mitigated by regex update)

### Neutral
- None remains valid for new entities
- Pattern matches Asana's current GID format
- Temp GIDs allowed for internal use

## Compliance

How do we ensure this decision is followed?

1. **Implementation**: Validation in ChangeTracker.track()
2. **Testing**: Unit tests for all valid/invalid patterns
3. **Boundary Tests**: FR-TEST-003, FR-TEST-004 from PRD-0009
4. **Error Messages**: Include format hint in ValidationError
5. **Documentation**: Document valid GID formats in limitations.md
