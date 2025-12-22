# ADR-0106: Template Discovery Pattern

## Status

Accepted

## Context

Pipeline conversion requires finding a template task in the target project to clone. Template tasks live in "Template" sections and serve as blueprints for new Processes. The system must:
1. Find the template section in a project
2. Identify the correct template task to clone
3. Handle missing templates gracefully

**Requirements**:
- FR-004: Template discovery with fuzzy matching

**Options Considered**:

1. **Option A: Exact Section Name Match** - Section must be named exactly "Template"
2. **Option B: Fuzzy Section Matching** - Section name contains "template" (case-insensitive)
3. **Option C: Configuration-Based** - Template section GID specified in config

## Decision

**We will use Option B: Fuzzy Section Matching.**

TemplateDiscovery searches for sections where the name contains "template" (case-insensitive). This matches common naming conventions like "Template", "Templates", "Template Tasks", "Process Templates", etc.

## Consequences

### Positive

- **Flexibility**: Works with various naming conventions
- **User-Friendly**: No strict naming requirements
- **Consistent**: Same pattern as ProcessSection.from_name() fuzzy matching

### Negative

- **Ambiguity**: Multiple sections might match (first match wins)
- **False Positives**: Section named "Template Review" would match

### Implementation

```python
class TemplateDiscovery:
    """Discovers template sections and tasks in target projects."""

    TEMPLATE_PATTERNS = ["template", "templates", "template tasks"]

    async def find_template_section_async(
        self, project_gid: str
    ) -> Section | None:
        """Find template section in project.

        Matches sections where name contains "template" (case-insensitive).
        Returns first matching section, or None if not found.
        """
        sections = await self._client.sections.list_async(project_gid)

        for section in sections:
            section_name_lower = section.name.lower()
            for pattern in self.TEMPLATE_PATTERNS:
                if pattern in section_name_lower:
                    return section

        return None

    async def find_template_task_async(
        self, project_gid: str, template_name: str | None = None
    ) -> Task | None:
        """Find template task for cloning.

        Args:
            project_gid: Project to search
            template_name: Optional specific template name

        Returns:
            First task in template section (or specific match if name given)
        """
        section = await self.find_template_section_async(project_gid)
        if section is None:
            return None

        tasks = await self._client.tasks.list_for_section_async(section.gid)

        if template_name:
            # Match specific template by name
            for task in tasks:
                if task.name.lower() == template_name.lower():
                    return task
            return None

        # Return first task as default template
        return tasks[0] if tasks else None
```

### Error Handling

When template is not found, AutomationResult includes descriptive error:
- `"No template section found in project {gid}"`
- `"No tasks in template section"`
- `"Template '{name}' not found in template section"`

## References

- TDD-AUTOMATION-LAYER (TemplateDiscovery Component section)
- PRD-AUTOMATION-LAYER (FR-004)
- DISCOVERY-AUTOMATION-LAYER (Section 3: Template Section Naming Patterns)
- ADR-0097: ProcessSection State Machine (fuzzy matching precedent)
