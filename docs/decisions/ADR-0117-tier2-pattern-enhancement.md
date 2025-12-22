# ADR-0117: Detection Tier 2 Pattern Matching Enhancement

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-19
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-TECH-DEBT-REMEDIATION (FR-DET-005), ADR-0094, TDD-TECH-DEBT-REMEDIATION

## Context

Detection Tier 2 uses name pattern matching to identify entity types when Tier 1 (project membership) fails. The current implementation uses simple substring matching:

```python
# Current: Simple contains matching
for pattern, entity_type in NAME_PATTERNS.items():
    if pattern in name_lower:
        return entity_type
```

This fails for **decorated names** - task names that include prefixes, suffixes, or embedded business context:

| Decorated Name | Expected Type | Current Result |
|----------------|---------------|----------------|
| `[URGENT] Contacts` | CONTACT_HOLDER | CONTACT_HOLDER (works) |
| `Acme Corp - Chiropractic Offers` | OFFER_HOLDER | OFFER_HOLDER (works) |
| `>> Processes <<` | PROCESS_HOLDER | PROCESS_HOLDER (works) |
| `Contacts (Primary)` | CONTACT_HOLDER | CONTACT_HOLDER (works) |
| `Contact List` | CONTACT_HOLDER | **UNKNOWN** (fails - "contacts" not matched) |
| `Unit 1` | UNIT | **UNKNOWN** (fails - "units" not in name) |
| `Offer - Premium Package` | OFFER | **UNKNOWN** (fails - "offers" not matched) |

### Problem Analysis

1. **Singular vs plural mismatch**: Pattern is "contacts" but task named "Contact List"
2. **Word boundary issues**: "Unit 1" should match but pattern "units" requires plural
3. **Embedded patterns**: "Contacts (Primary)" works, but "Primary Contacts" may not be ideal
4. **False positives risk**: "Recontact List" contains "contact" - is this a Contact?

### Forces

1. **Accuracy**: Must correctly identify entity types from decorated names
2. **Specificity**: Avoid false positives from incidental substring matches
3. **Performance**: O(1) string operations; no regex compilation per call
4. **Maintainability**: Pattern rules should be declarative and easy to extend
5. **Backward compatibility**: Existing correct matches must continue working

## Decision

Enhance Tier 2 detection with **word boundary-aware pattern matching** using **both singular and plural forms** with **optional prefix/suffix stripping**.

### Enhanced Pattern Matching

```python
# Pattern configuration with variants
PATTERN_CONFIG: dict[EntityType, PatternSpec] = {
    EntityType.CONTACT_HOLDER: PatternSpec(
        patterns=["contacts", "contact"],
        word_boundary=True,  # Match whole words only
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
    # ... additional patterns
}
```

### Word Boundary Matching

Use regex with word boundaries for accurate matching:

```python
import re
from functools import lru_cache

@lru_cache(maxsize=128)
def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile pattern with word boundary markers."""
    # \b matches word boundaries (start/end of word)
    return re.compile(rf"\b{re.escape(pattern)}\b", re.IGNORECASE)

def _matches_pattern(name: str, patterns: list[str]) -> bool:
    """Check if name matches any pattern with word boundaries."""
    for pattern in patterns:
        compiled = _compile_pattern(pattern)
        if compiled.search(name):
            return True
    return False
```

### Decoration Stripping

Strip common prefixes/suffixes before matching:

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
    """Remove common task name decorations."""
    result = name
    for pattern in STRIP_PATTERNS:
        result = re.sub(pattern, "", result)
    return result.strip()
```

### Implementation

```python
@dataclass(frozen=True, slots=True)
class PatternSpec:
    """Configuration for entity type pattern matching."""
    patterns: list[str]
    word_boundary: bool = True
    strip_decorations: bool = True


def _detect_by_name_pattern(task: Task) -> DetectionResult | None:
    """Tier 2: Enhanced name pattern matching.

    Per ADR-0117: Word boundary matching with decoration stripping.
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
                    confidence=CONFIDENCE_TIER_2,
                    tier_used=2,
                    needs_healing=True,
                    expected_project_gid=expected_gid,
                )

    return None
```

### Pattern Priority

Patterns are checked in specificity order (longer/more specific patterns first):

```python
# Pattern priority order (most specific first)
PATTERN_PRIORITY = [
    EntityType.CONTACT_HOLDER,     # "contacts", "contact"
    EntityType.UNIT_HOLDER,        # "units", "unit", "business units"
    EntityType.OFFER_HOLDER,       # "offers", "offer"
    EntityType.PROCESS_HOLDER,     # "processes", "process"
    EntityType.LOCATION_HOLDER,    # "location"
    EntityType.DNA_HOLDER,         # "dna"
    EntityType.ASSET_EDIT_HOLDER,  # "asset edit", "asset edits"
    EntityType.VIDEOGRAPHY_HOLDER, # "videography"
]
```

### Test Cases for Validation

| Input Name | Expected Match | Matched By |
|------------|----------------|------------|
| `Contacts` | CONTACT_HOLDER | "contacts" word match |
| `Contact` | CONTACT_HOLDER | "contact" word match |
| `[URGENT] Contacts` | CONTACT_HOLDER | stripped + "contacts" |
| `Acme - Contacts (Primary)` | CONTACT_HOLDER | stripped + "contacts" |
| `Contact List` | CONTACT_HOLDER | "contact" word match |
| `Recontact Team` | **None** | "contact" not at word boundary |
| `Unit 1` | UNIT_HOLDER | "unit" word match |
| `Units` | UNIT_HOLDER | "units" word match |
| `Community` | **None** | "unit" substring but not word boundary |
| `Offers` | OFFER_HOLDER | "offers" word match |
| `Special Offer` | OFFER_HOLDER | "offer" word match |
| `Prooffer` | **None** | "offer" not at word boundary |

## Alternatives Considered

### Alternative A: Pure Substring Matching (Current)

- **Description**: Keep existing `pattern in name_lower` matching
- **Pros**: Simple; fast; no regex overhead
- **Cons**: Misses singular forms; no word boundary protection
- **Why not chosen**: 95% accuracy target requires better matching

### Alternative B: Fuzzy Matching (Levenshtein Distance)

- **Description**: Use edit distance to find close matches
- **Pros**: Handles typos and variations
- **Cons**: Complex; slow; unpredictable results; false positives
- **Why not chosen**: Overkill for structured task names; unpredictable

### Alternative C: ML-Based Classification

- **Description**: Train classifier on task name patterns
- **Pros**: Handles edge cases automatically; learns from data
- **Cons**: Heavy dependency; training data required; black box
- **Why not chosen**: Way overkill; simple rules are sufficient

### Alternative D: Configurable Regex Per Pattern

- **Description**: Allow full regex syntax in pattern configuration
- **Pros**: Maximum flexibility
- **Cons**: Complex to maintain; easy to write bad patterns; security concerns
- **Why not chosen**: Word boundary matching covers needs without full regex complexity

## Consequences

### Positive

- **Higher accuracy**: Word boundary matching prevents false positives
- **Singular/plural support**: Both forms matched for each entity type
- **Decoration resilience**: Prefixes/suffixes stripped before matching
- **Cached compilation**: Regex patterns compiled once and cached
- **Declarative config**: Pattern rules easy to read and extend
- **95% accuracy achievable**: Per FR-DET-005 target

### Negative

- **Regex overhead**: Small performance cost vs simple substring (mitigated by caching)
- **More complex code**: Pattern matching logic is more involved
- **New edge cases**: Some decorated names may not match (document and iterate)

### Neutral

- Pattern configuration becomes the source of truth
- Existing correct matches continue working
- Detection result structure unchanged

## Compliance

- Pattern matching MUST use word boundary-aware regex
- PATTERN_CONFIG MUST include both singular and plural forms
- Decoration stripping MUST be applied before pattern matching
- Regex patterns MUST be compiled with `lru_cache` for performance
- Tests MUST verify all decorated name examples from PRD
- Accuracy MUST be >= 95% on decorated name test suite per FR-DET-005
- False positive rate MUST be < 1% (e.g., "Community" not matching "unit")
