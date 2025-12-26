# ADR-0055: State and Discovery Patterns

## Metadata
- **Status**: Accepted
- **Consolidated From**: ADR-0097 (ProcessSection State Machine), ADR-0100 (State Transition Composition), ADR-0093 (Project-EntityType Registry), ADR-0106 (Template Discovery), ADR-0113 (Rep Field Cascade), ADR-0138 (Tier 2 Pattern Enhancement)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Related**: [reference/PATTERNS.md](reference/PATTERNS.md), ADR-SUMMARY-DETECTION

---

## Context

The SDK needs patterns for:
1. **State management**: Pipeline processes move through stages (Opportunity → Active → Converted)
2. **Entity type discovery**: Determining Business vs Contact vs Unit from Asana tasks
3. **Template discovery**: Finding template sections and tasks in projects
4. **Field cascading**: Resolving values from parent entities (Unit.rep → Business.rep)
5. **Pattern matching**: Robust name-based entity detection with decorations

These patterns require balancing flexibility (support variations) with reliability (deterministic behavior).

---

## Decision

Use **enum-based state machines** with fuzzy matching, **registry patterns** for O(1) lookup, and **cascade resolution** with specificity rules.

### 1. ProcessSection State Machine

**Purpose**: Represent pipeline states via enum with section membership as source of truth.

**Decision**: No enforced state transitions—SDK provides primitives, consumers implement rules.

```python
class ProcessSection(str, Enum):
    """Pipeline state represented by Asana section membership."""
    OPPORTUNITY = "opportunity"
    DELAYED = "delayed"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"  # Fallback for unknown sections

    @classmethod
    def from_name(cls, name: str | None) -> ProcessSection | None:
        """Convert section name to enum with fuzzy matching.

        Normalization:
        - Lowercase
        - Replace spaces/hyphens with underscores
        - Strip whitespace

        Aliases:
        - "Lost" → DID_NOT_CONVERT
        - "Didn't Convert" → DID_NOT_CONVERT
        - "In Progress" → ACTIVE

        Args:
            name: Section name from Asana.

        Returns:
            ProcessSection enum value, OTHER for unrecognized, None for None input.

        Example:
            >>> ProcessSection.from_name("Did Not Convert")
            ProcessSection.DID_NOT_CONVERT

            >>> ProcessSection.from_name("Lost")
            ProcessSection.DID_NOT_CONVERT

            >>> ProcessSection.from_name("Custom Section")
            ProcessSection.OTHER
        """
        if name is None:
            return None

        # Normalize: lowercase, replace spaces/hyphens
        normalized = name.lower().replace(" ", "_").replace("-", "_").strip()

        # Try exact match
        try:
            return cls(normalized)
        except ValueError:
            pass

        # Try aliases
        ALIASES = {
            "lost": cls.DID_NOT_CONVERT,
            "didnt_convert": cls.DID_NOT_CONVERT,
            "didn't_convert": cls.DID_NOT_CONVERT,
            "in_progress": cls.ACTIVE,
        }
        if normalized in ALIASES:
            return ALIASES[normalized]

        # Unrecognized
        return cls.OTHER
```

**State Extraction**:

```python
@property
def pipeline_state(self) -> ProcessSection | None:
    """Extract current pipeline state from section membership.

    Returns:
        ProcessSection enum value or None if not in pipeline project.

    Example:
        >>> process.pipeline_state
        ProcessSection.OPPORTUNITY
    """
    # Find pipeline project membership via ProcessProjectRegistry
    pipeline_membership = self._find_pipeline_membership()
    if pipeline_membership is None:
        return None

    section_name = pipeline_membership.get("section", {}).get("name")
    return ProcessSection.from_name(section_name)
```

**State Transition Composition**:

```python
# Process.move_to_state() wraps SaveSession.move_to_section()
def move_to_state(
    self,
    session: SaveSession,
    target_state: ProcessSection
) -> SaveSession:
    """Move process to target pipeline state.

    This is a convenience method that wraps session.move_to_section()
    with ProcessProjectRegistry lookup.

    Args:
        session: Active SaveSession.
        target_state: Desired ProcessSection.

    Returns:
        session for fluent chaining.

    Raises:
        ValueError: If target section not configured for process type.

    Example:
        async with client.save_session() as session:
            process.move_to_state(session, ProcessSection.CONVERTED)
            await session.commit_async()
    """
    # Look up section GID via registry
    section_gid = ProcessProjectRegistry.get_section_gid(
        self.process_type,
        target_state
    )
    if section_gid is None:
        raise ValueError(
            f"No section configured for {self.process_type.value} "
            f"process in state {target_state.value}"
        )

    # Delegate to session primitive
    return session.move_to_section(self, section_gid)
```

**Rationale**:
- **Section membership is source of truth**: Matches Asana board view
- **No state transition enforcement**: Business rules belong in consumers, not SDK
- **Fuzzy matching with aliases**: Handles section name variations
- **OTHER fallback**: Custom sections don't cause errors

### 2. Project-to-EntityType Registry

**Purpose**: O(1) deterministic detection via import-time population.

```python
class ProjectTypeRegistry:
    """Singleton registry for project GID to EntityType mapping.

    Populated automatically via __init_subclass__ hook when business
    entities define PRIMARY_PROJECT_GID class attribute.
    """

    _instance: ProjectTypeRegistry | None = None
    _registry: dict[str, EntityType] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, project_gid: str, entity_type: EntityType) -> None:
        """Register project GID to entity type mapping.

        Args:
            project_gid: Asana project GID.
            entity_type: EntityType enum value.
        """
        self._registry[project_gid] = entity_type

    def get_entity_type(self, project_gid: str) -> EntityType | None:
        """Lookup entity type by project GID.

        Args:
            project_gid: Asana project GID.

        Returns:
            EntityType if registered, None otherwise.

        Example:
            >>> registry.get_entity_type("123456")
            EntityType.BUSINESS
        """
        return self._registry.get(project_gid)
```

**Auto-Population via `__init_subclass__`**:

```python
class BusinessEntity(Task):
    """Base class for business entities with auto-registration."""

    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Get project GID from environment or class attribute
        env_var = f"ASANA_PROJECT_{cls.__name__.upper()}"
        project_gid = os.getenv(env_var) or cls.PRIMARY_PROJECT_GID

        if project_gid:
            registry = ProjectTypeRegistry()
            entity_type = EntityType(cls.__name__)
            registry.register(project_gid, entity_type)


# Usage: class attribute triggers registration
class Business(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "123456"  # Auto-registers


# Environment override takes precedence
# ASANA_PROJECT_BUSINESS=789012  # Overrides class attribute
```

**Override Hierarchy**: Env var > class attribute > None

**Rationale**:
- **O(1) lookup**: Dict-based for deterministic detection
- **Import-time population**: Registry ready when needed
- **Environment override**: Deploy-time configuration without code changes
- **Explicit registration**: No magic, clear ownership

### 3. Template Discovery Pattern

**Purpose**: Fuzzy matching for template sections and tasks.

```python
class TemplateDiscovery:
    """Discover template sections and tasks in projects."""

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def find_template_section_async(
        self, project_gid: str
    ) -> Section | None:
        """Find template section in project via fuzzy name matching.

        Patterns matched (case-insensitive):
        - "template"
        - "templates"
        - "template tasks"
        - "process templates"

        Args:
            project_gid: Asana project GID.

        Returns:
            First section matching template pattern, None if not found.

        Example:
            discovery = TemplateDiscovery(client)
            template_section = await discovery.find_template_section_async("123456")
            if template_section:
                print(f"Found: {template_section.name}")
        """
        sections = await self._client.sections.list_for_project_async(project_gid)

        for section in sections:
            if "template" in section.name.lower():
                return section

        return None

    async def find_template_task_async(
        self,
        project_gid: str,
        template_name: str | None = None
    ) -> Task | None:
        """Find template task in template section.

        Args:
            project_gid: Asana project GID.
            template_name: Optional specific template name to match.

        Returns:
            First task in template section, or specific match if name provided.

        Example:
            # Get first template task
            task = await discovery.find_template_task_async("123456")

            # Get specific template
            task = await discovery.find_template_task_async(
                "123456",
                template_name="Sales Process Template"
            )
        """
        template_section = await self.find_template_section_async(project_gid)
        if template_section is None:
            return None

        tasks = await self._client.tasks.list_for_section_async(template_section.gid)

        if template_name is None:
            # Return first task
            return next(iter(tasks), None)

        # Find specific template by name
        for task in tasks:
            if template_name.lower() in task.name.lower():
                return task

        return None
```

**Rationale**:
- **Fuzzy matching**: Section names vary ("Template", "Templates", "Process Templates")
- **First match**: Simple and predictable
- **Returns None on error**: Descriptive error in AutomationResult
- **No configuration required**: Discovery-based

### 4. Rep Field Cascade Pattern

**Purpose**: Resolve values from entity hierarchy with specificity rules.

```python
def resolve_rep(unit: Unit | None, business: Business | None) -> str | None:
    """Resolve rep field via cascading with specificity principle.

    Cascade order (more specific wins):
    1. Unit.rep
    2. Business.rep

    Args:
        unit: Unit entity (may have rep override).
        business: Business entity (fallback for rep).

    Returns:
        Rep GID if found, None otherwise.

    Example:
        # Unit has override
        rep_gid = resolve_rep(unit, business)  # Returns unit.rep

        # Unit has no rep, falls back
        rep_gid = resolve_rep(unit_without_rep, business)  # Returns business.rep

        # No rep at any level
        rep_gid = resolve_rep(None, business_without_rep)  # Returns None, logs warning
    """
    # Unit.rep takes precedence (specificity principle)
    if unit and unit.rep:
        return unit.rep[0]["gid"]

    # Fall back to Business.rep
    if business and business.rep:
        return business.rep[0]["gid"]

    # No rep found, log warning
    logger.warning(
        "no_rep_resolved",
        extra={
            "unit_gid": unit.gid if unit else None,
            "business_gid": business.gid if business else None
        }
    )
    return None
```

**Use Case**: Assign rep to new Process during pipeline conversion.

**Rationale**:
- **Specificity principle**: More specific entity wins (Unit > Business)
- **Graceful fallback**: Empty rep doesn't fail conversion
- **Clear cascade order**: Documented and predictable

### 5. Tier 2 Pattern Matching Enhancement

**Purpose**: Word boundary-aware regex matching with decoration stripping.

```python
PATTERN_CONFIG = {
    EntityType.CONTACT_HOLDER: PatternSpec(
        patterns=["contacts", "contact"],  # Singular + plural
        word_boundary=True,  # Match whole words only
        strip_decorations=True,  # Remove [URGENT] prefixes, (Primary) suffixes
    ),
}

def _strip_decorations(name: str) -> str:
    """Strip common task name decorations.

    Patterns removed:
    - Bracketed prefixes: [URGENT], [HIGH]
    - Angle brackets: >>, <<
    - Parenthetical suffixes: (Primary), (Backup)
    - Numeric prefixes: "1. ", "2. "
    - Dash prefixes: "- "

    Args:
        name: Task name from Asana.

    Returns:
        Name with decorations removed.

    Example:
        >>> _strip_decorations("[URGENT] Contacts")
        "Contacts"

        >>> _strip_decorations("1. Contact List (Primary)")
        "Contact List"
    """
    # Remove bracketed prefixes
    name = re.sub(r"^\[[^\]]+\]\s*", "", name)
    # Remove angle brackets
    name = re.sub(r"^[><]+\s*", "", name)
    # Remove parenthetical suffixes
    name = re.sub(r"\s*\([^)]+\)$", "", name)
    # Remove numeric/dash prefixes
    name = re.sub(r"^[\d\-]+\.\s*", "", name)
    return name.strip()


def _matches_pattern(name: str, patterns: list[str]) -> bool:
    """Check if name matches any pattern with word boundaries.

    Args:
        name: Task name (decorations already stripped).
        patterns: List of patterns to match.

    Returns:
        True if any pattern matches.

    Example:
        >>> _matches_pattern("Contact List", ["contact", "contacts"])
        True  # "contact" matches

        >>> _matches_pattern("Recontact Team", ["contact", "contacts"])
        False  # Word boundary prevents "contact" in "Recontact"
    """
    for pattern in patterns:
        # \\b ensures word boundary (no "contact" in "Recontact")
        if re.search(rf"\b{re.escape(pattern)}\b", name, re.IGNORECASE):
            return True
    return False
```

**Test Cases**:

| Input | Matches CONTACT_HOLDER? | Reason |
|-------|------------------------|--------|
| "Contact List" | YES | "contact" matches |
| "Contacts" | YES | "contacts" matches |
| "Recontact Team" | NO | Word boundary prevents match |
| "[URGENT] Contacts" | YES | Decoration stripped before match |
| "1. Contact List (Primary)" | YES | All decorations stripped |

**Rationale**:
- **Word boundaries**: Prevent false positives ("contact" in "Recontact")
- **Decoration stripping**: Handles user formatting variations
- **Performance**: Regex patterns compiled with `@lru_cache`

---

## Rationale

### Why Enum-Based State Machine?

| State Source | Pros | Cons |
|--------------|------|------|
| **Section membership** | **Matches Asana UI, already in memberships** | Requires project GID |
| Custom field | Explicit, independent | Requires API call, may be out of sync |
| Task property | Built into model | No such property exists |

Section membership is canonical representation in Asana board view.

### Why No State Transition Enforcement?

Per PRD scope: "SDK enables transitions, does not enforce sequences."

Reasons:
- Different workflows have different valid transitions
- Business rules belong in consumers
- Enforcement requires maintaining rules per ProcessType
- Stakeholders may legitimately skip states

SDK provides primitive (`move_to_state`), consumers implement rules.

### Why Registry Pattern?

**Benefits**:
- **O(1) lookup**: Dict-based, no iteration
- **Import-time population**: No runtime discovery overhead
- **Deterministic**: Explicit registration via class attribute
- **Testable**: Can inject test registries

**Alternative** (runtime discovery): Scan all projects at startup.
- **Rejected**: Slow, requires API calls, fragile

### Why Template Discovery Over Configuration?

**Alternative**: Require users to configure template section GID.
- **Rejected**: Discovery reduces configuration burden; fuzzy matching handles variations

**Trade-off**: Discovery may find wrong section if multiple have "template" in name.
- **Mitigation**: Returns first match; users can override via specific GID if needed

### Why Cascade Resolution?

**Benefits**:
- **DRY**: Set value once at Business level, all Units inherit
- **Override capability**: Unit can override with specific value
- **Clear precedence**: More specific always wins

**Use case**: Rep field cascades from Business to Unit to Process during creation.

---

## Alternatives Considered

### State Machine Alternatives

#### Alternative 1: State Machine with Validation

- **Description**: Define valid transitions per ProcessType, raise error on invalid moves
- **Pros**: Prevents invalid states, self-documenting rules
- **Cons**: SDK must know all business rules, inflexible
- **Why not chosen**: Business logic belongs in consumers

#### Alternative 2: Custom Field for State

- **Description**: Use "Pipeline State" custom field instead of section
- **Pros**: Independent of section, explicit value
- **Cons**: Requires API call, can become out of sync, doesn't match UI
- **Why not chosen**: Section membership is source of truth

#### Alternative 3: Dynamic Section Enum

- **Description**: Generate ProcessSection from actual sections in projects
- **Pros**: Always matches reality
- **Cons**: Requires API call at import, unpredictable enum values, no IDE support
- **Why not chosen**: Over-engineering; fixed enum with OTHER handles requirements

### Discovery Alternatives

#### Alternative 1: Strict Section Name Matching

- **Description**: Only accept exact section names, error on mismatch
- **Pros**: Explicit, catches configuration errors
- **Cons**: Brittle, breaks if user renames
- **Why not chosen**: Fuzzy matching more robust

#### Alternative 2: Configuration-Only (No Discovery)

- **Description**: Require all template section GIDs in config
- **Pros**: Explicit, no ambiguity
- **Cons**: Configuration burden, maintenance overhead
- **Why not chosen**: Discovery reduces friction

---

## Consequences

### Positive

1. **ProcessSection**:
   - Clear type safety for pipeline states
   - Matches Asana UI (board sections)
   - Robust name matching with aliases
   - No API calls for state extraction
   - Flexible: OTHER handles custom sections

2. **Project Registry**:
   - O(1) deterministic detection
   - Import-time population (no runtime cost)
   - Environment override support
   - Clear ownership per entity type

3. **Template Discovery**:
   - Reduces configuration burden
   - Handles section name variations
   - Returns None (not error) for resilience

4. **Cascade Resolution**:
   - DRY: set once at Business level
   - Override capability at Unit level
   - Clear precedence rules

5. **Pattern Matching**:
   - Word boundaries prevent false positives
   - Decoration stripping handles formatting
   - Singular/plural support

### Negative

1. **ProcessSection**:
   - SDK does not enforce transitions (consumer responsibility)
   - Alias list may need maintenance
   - OTHER provides less information than specific state

2. **Project Registry**:
   - Requires class attribute or env var
   - Singleton pattern (global state)

3. **Template Discovery**:
   - First match may not be intended section
   - No configuration override (must use specific GID)

4. **Cascade Resolution**:
   - Cascade logic must be maintained
   - Target types vary per entity

5. **Pattern Matching**:
   - Regex compilation overhead (mitigated by `@lru_cache`)

### Neutral

1. **from_name() overhead**: String normalization (minimal)
2. **Section GID configuration**: Optional (name matching sufficient)
3. **Logging**: Warnings for missing values (rep, template)

---

## Compliance

### How This Decision Will Be Enforced

1. **ProcessSection**:
   - [ ] Enum has 7 values (OPPORTUNITY through OTHER)
   - [ ] from_name() is case-insensitive
   - [ ] from_name() returns OTHER for unrecognized
   - [ ] from_name() returns None for None input
   - [ ] No state transition validation in SDK
   - [ ] Alias list documented in code comments

2. **Project Registry**:
   - [ ] ProjectTypeRegistry is singleton
   - [ ] __init_subclass__ registers PRIMARY_PROJECT_GID
   - [ ] Environment variable overrides class attribute
   - [ ] get_entity_type() returns None for unregistered

3. **Template Discovery**:
   - [ ] find_template_section_async() uses fuzzy matching
   - [ ] Returns None (not error) when not found
   - [ ] First match returned

4. **Cascade Resolution**:
   - [ ] More specific entity takes precedence
   - [ ] Returns None for missing values (logs warning)
   - [ ] Use case documented (Process creation)

5. **Pattern Matching**:
   - [ ] Word boundary regex used
   - [ ] Decorations stripped before matching
   - [ ] Singular + plural patterns
   - [ ] Test coverage for edge cases

---

**Related**: ADR-SUMMARY-DETECTION (multi-tier detection), ADR-SUMMARY-CUSTOM-FIELDS (cascading), reference/PATTERNS.md (full catalog)

**Supersedes**: Individual ADRs ADR-0097, ADR-0100, ADR-0093, ADR-0106, ADR-0113, ADR-0138
