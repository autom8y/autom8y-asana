# ADR-0021: Detection Pattern Matching Enhancement

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: SDK Team
- **Consolidated From**: ADR-0138
- **Related**: [reference/DETECTION.md](reference/DETECTION.md), ADR-0020, PRD-TECH-DEBT-REMEDIATION

## Context

Detection Tier 2 uses name pattern matching to identify entity types when Tier 1 (project membership) fails. This tier must handle **decorated task names** - names that include prefixes, suffixes, or embedded business context common in real-world Asana usage.

### Problem: Simple Substring Matching Failures

The original implementation used simple substring matching:

```python
# Original: Simple contains matching
for pattern, entity_type in NAME_PATTERNS.items():
    if pattern in name_lower:
        return entity_type
```

This fails for common decorated names:

| Decorated Name | Expected Type | Substring Result | Issue |
|----------------|---------------|------------------|-------|
| `Contact List` | CONTACT_HOLDER | **UNKNOWN** | "contacts" not matched (singular vs plural) |
| `Unit 1` | UNIT_HOLDER | **UNKNOWN** | "units" not in name (plural expected) |
| `Offer - Premium Package` | OFFER_HOLDER | **UNKNOWN** | "offers" not matched (singular) |
| `Community` | Should be UNKNOWN | **UNIT_HOLDER** | False positive ("unit" substring) |
| `Recontact Team` | Should be UNKNOWN | **CONTACT_HOLDER** | False positive ("contact" substring) |

### Requirements

1. **Accuracy**: 95%+ success rate on decorated names (FR-DET-005)
2. **Specificity**: <1% false positive rate (avoid "Community" → UNIT)
3. **Performance**: O(1) operations; no expensive regex compilation per call
4. **Maintainability**: Declarative pattern rules, easy to extend
5. **Backward compatibility**: Existing correct matches must continue working

## Decision

We will implement **word boundary-aware pattern matching** with **singular/plural support** and **decoration stripping**.

### Pattern Configuration

```python
@dataclass(frozen=True, slots=True)
class PatternSpec:
    """Configuration for entity type pattern matching."""
    patterns: list[str]  # Both singular and plural forms
    word_boundary: bool = True  # Match whole words only
    strip_decorations: bool = True  # Remove common prefixes/suffixes

# Pattern configuration with variants
PATTERN_CONFIG: dict[EntityType, PatternSpec] = {
    EntityType.CONTACT_HOLDER: PatternSpec(
        patterns=["contacts", "contact"],
        word_boundary=True,
        strip_decorations=True,
    ),
    EntityType.UNIT_HOLDER: PatternSpec(
        patterns=["units", "unit", "business units"],
        word_boundary=True,
        strip_decorations=True,
    ),
    EntityType.OFFER_HOLDER: PatternSpec(
        patterns=["offers", "offer"],
        word_boundary=True,
        strip_decorations=True,
    ),
    EntityType.PROCESS_HOLDER: PatternSpec(
        patterns=["processes", "process"],
        word_boundary=True,
        strip_decorations=True,
    ),
    EntityType.LOCATION_HOLDER: PatternSpec(
        patterns=["location", "address"],
        word_boundary=True,
        strip_decorations=True,
    ),
    # ... additional entity types
}
```

### Word Boundary Matching

Use regex with word boundaries (`\b`) to prevent substring false positives:

```python
import re
from functools import lru_cache

@lru_cache(maxsize=128)
def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile pattern with word boundary markers.

    Cached to avoid repeated compilation overhead.
    """
    # \b matches word boundaries (start/end of word)
    return re.compile(rf"\b{re.escape(pattern)}\b", re.IGNORECASE)


def _matches_pattern(
    name: str,
    patterns: list[str],
    word_boundary: bool = True,
) -> bool:
    """Check if name matches any pattern.

    Args:
        name: Task name to check
        patterns: List of patterns to match against
        word_boundary: If True, use word boundary matching

    Returns:
        True if any pattern matches
    """
    for pattern in patterns:
        if word_boundary:
            compiled = _compile_pattern(pattern)
            if compiled.search(name):
                return True
        else:
            # Fallback to substring matching if word_boundary=False
            if pattern in name.lower():
                return True
    return False
```

**Example matches**:
- `"Contact List"` matches `\bcontact\b` ✓
- `"Unit 1"` matches `\bunit\b` ✓
- `"Community"` does NOT match `\bunit\b` ✓ (false positive prevented)
- `"Recontact Team"` does NOT match `\bcontact\b` ✓ (false positive prevented)

### Decoration Stripping

Strip common prefixes and suffixes before pattern matching:

```python
# Common decorations to strip
STRIP_PATTERNS = [
    r"^\[.*?\]\s*",      # [URGENT] prefix
    r"^>+\s*",           # >> prefix
    r"\s*<+$",           # << suffix
    r"\s*\(.*?\)$",      # (Primary) suffix
    r"^\d+\.\s*",        # "1. " numbered prefix
    r"^[-*]\s*",         # "- " or "* " bullet prefix
]

def _strip_decorations(name: str) -> str:
    """Remove common task name decorations.

    Args:
        name: Original task name

    Returns:
        Name with decorations stripped

    Examples:
        >>> _strip_decorations("[URGENT] Contacts")
        'Contacts'
        >>> _strip_decorations("Contacts (Primary)")
        'Contacts'
        >>> _strip_decorations(">> Processes <<")
        'Processes'
    """
    result = name
    for pattern in STRIP_PATTERNS:
        result = re.sub(pattern, "", result)
    return result.strip()
```

### Tier 2 Implementation

```python
def _detect_by_name_pattern(task: Task) -> DetectionResult | None:
    """Tier 2: Enhanced name pattern matching.

    Per ADR-0021: Word boundary matching with decoration stripping.

    Args:
        task: Task to detect type for

    Returns:
        DetectionResult if pattern matches, None otherwise
    """
    if not task.name:
        return None

    # Prepare name variants
    name_original = task.name
    name_stripped = _strip_decorations(name_original)

    # Try each entity type's patterns
    for entity_type, spec in PATTERN_CONFIG.items():
        # Check both original and stripped names
        names_to_check = [name_original, name_stripped]

        for name in names_to_check:
            if _matches_pattern(name, spec.patterns, spec.word_boundary):
                expected_gid = get_registry().get_primary_gid(entity_type)
                return DetectionResult(
                    entity_type=entity_type,
                    confidence=0.6,  # Tier 2 confidence
                    tier_used=2,
                    needs_healing=True,
                    expected_project_gid=expected_gid,
                )

    return None
```

### Validation Test Cases

| Input Name | Expected Match | Matched By | Confidence |
|------------|----------------|------------|------------|
| `Contacts` | CONTACT_HOLDER | "contacts" word match | 60% |
| `Contact` | CONTACT_HOLDER | "contact" word match | 60% |
| `[URGENT] Contacts` | CONTACT_HOLDER | stripped + "contacts" | 60% |
| `Acme - Contacts (Primary)` | CONTACT_HOLDER | stripped + "contacts" | 60% |
| `Contact List` | CONTACT_HOLDER | "contact" word match | 60% |
| `Recontact Team` | **None** | "contact" not at boundary | N/A |
| `Unit 1` | UNIT_HOLDER | "unit" word match | 60% |
| `Units` | UNIT_HOLDER | "units" word match | 60% |
| `Community` | **None** | "unit" substring but not boundary | N/A |
| `Offers` | OFFER_HOLDER | "offers" word match | 60% |
| `Special Offer` | OFFER_HOLDER | "offer" word match | 60% |
| `Prooffer` | **None** | "offer" not at boundary | N/A |

## Rationale

### Why Word Boundaries?

Without word boundaries:
- `"Community"` matches `"unit"` (substring false positive)
- `"Recontact"` matches `"contact"` (prefix false positive)
- `"Prooffer"` matches `"offer"` (embedded false positive)

With word boundaries (`\b`):
- Only matches complete words
- Prevents substring false positives
- Achieves <1% false positive rate

### Why Decoration Stripping?

Real-world Asana usage includes decorations:
- Priority markers: `[URGENT]`, `!!`, `***`
- Visual separators: `>>`, `--`, `==`
- Contextual suffixes: `(Primary)`, `(Backup)`, `(Archive)`
- List formatting: `1.`, `*`, `-`

Stripping before matching handles these without expanding pattern complexity.

### Why Both Singular and Plural?

Task names vary by team preference:
- Some teams use `"Contact"` (singular)
- Some teams use `"Contacts"` (plural)
- Entity type should detect both without preference

### Why lru_cache for Pattern Compilation?

Regex compilation has cost (~10μs per pattern). With caching:
- Compilation happens once per unique pattern
- Subsequent matches use cached compiled pattern
- Total overhead <1μs for cached patterns
- Maintains O(1) performance characteristic

### Why 60% Confidence for Tier 2?

Confidence reflects heuristic nature:
- **100%** (Tier 1): Deterministic project membership
- **60%** (Tier 2): Heuristic name patterns (this tier)
- **80%** (Tier 3): Structural parent-child relationships
- **95%** (Tier 4): Near-deterministic structure inspection
- **0%** (Tier 5): Unknown fallback

60% acknowledges that name patterns can be ambiguous but are generally reliable.

## Alternatives Considered

### Alternative A: Pure Substring Matching (Original)

```python
if "contacts" in name.lower():
    return EntityType.CONTACT_HOLDER
```

**Why not chosen**:
- Misses singular forms ("Contact List")
- False positives ("Community" → Unit)
- Cannot achieve 95% accuracy target

### Alternative B: Fuzzy Matching (Levenshtein Distance)

```python
if levenshtein_distance(name, "contacts") < 3:
    return EntityType.CONTACT_HOLDER
```

**Why not chosen**:
- Complex implementation
- Slow (O(n*m) per comparison)
- Unpredictable results on edge cases
- Overkill for structured task names

### Alternative C: ML-Based Classification

Train a classifier on task name patterns.

**Why not chosen**:
- Heavy dependency (scikit-learn, TensorFlow, etc.)
- Requires training data collection
- Black box decision making
- Overkill for rule-based domain
- Simple rules are sufficient and maintainable

### Alternative D: Full Regex Syntax Per Pattern

```python
PATTERNS = {
    EntityType.CONTACT_HOLDER: r"^(\[.*?\]\s*)?contacts?(\s*\(.*?\))?$",
}
```

**Why not chosen**:
- Complex to maintain
- Easy to write incorrect patterns
- Security concerns with arbitrary regex
- Word boundary matching covers needs without full regex complexity

## Consequences

### Positive

- **95%+ accuracy**: Word boundary matching achieves target accuracy
- **<1% false positives**: Prevents substring false matches
- **Singular/plural support**: Both forms matched for each entity type
- **Decoration resilience**: Common prefixes/suffixes handled gracefully
- **Performance maintained**: Cached compilation keeps overhead <1μs
- **Declarative configuration**: Pattern rules easy to read and extend
- **Backward compatible**: All existing correct matches continue working

### Negative

- **Regex overhead**: Small performance cost vs simple substring (mitigated by caching)
- **More complex code**: Pattern matching logic more involved than substring
- **New edge cases**: Some decorated names may not match (document and iterate)
- **Maintenance burden**: Strip patterns require updates for new decoration styles

### Neutral

- Pattern configuration becomes single source of truth
- Detection result structure unchanged
- Confidence level (60%) explicitly documented

## Compliance

How do we ensure this decision is followed?

1. **Pattern matching MUST use word boundary-aware regex** - verified by unit tests
2. **PATTERN_CONFIG MUST include both singular and plural forms** - enforced by code review
3. **Decoration stripping MUST be applied before pattern matching** - verified by implementation
4. **Regex patterns MUST be compiled with `lru_cache`** - performance requirement
5. **Accuracy MUST be >= 95% on decorated name test suite** - verified by integration tests
6. **False positive rate MUST be < 1%** - verified by negative test cases
7. **All decorated name examples from PRD MUST pass tests** - regression suite

## Implementation Notes

**Adding new entity types**:

```python
# Add pattern spec to configuration
PATTERN_CONFIG[EntityType.NEW_TYPE] = PatternSpec(
    patterns=["new_types", "new_type"],  # Plural and singular
    word_boundary=True,
    strip_decorations=True,
)
```

**Adding new decoration patterns**:

```python
# Add to STRIP_PATTERNS if new decoration style emerges
STRIP_PATTERNS.append(r"^!!!\s*")  # "!!! " prefix
```

**Performance monitoring**:

```python
# Log pattern matching performance
with timer("tier2_pattern_matching"):
    result = _detect_by_name_pattern(task)

# Alert if > 5ms (indicates cache miss or pattern issue)
```

**Testing pattern changes**:

```python
# Test both positive and negative cases
def test_word_boundary_prevents_false_positive():
    task = Task(name="Community Center", gid="123")
    result = _detect_by_name_pattern(task)
    assert result is None  # Should NOT match "unit"

def test_singular_form_matches():
    task = Task(name="Contact List", gid="123")
    result = _detect_by_name_pattern(task)
    assert result.entity_type == EntityType.CONTACT_HOLDER
```
