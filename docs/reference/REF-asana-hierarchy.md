# Asana Resource Hierarchy

## Metadata
- **Document Type**: Reference
- **Status**: Active
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Purpose**: Canonical reference for Asana's resource hierarchy and navigation patterns

## Overview

Asana organizes work in a hierarchical structure: **Workspace → Project → Section → Task → Subtask**. Understanding this hierarchy is critical for effective SDK usage, especially for navigation, relationship management, and multi-homing behavior.

## Hierarchy Structure

```
Workspace
  ├── Project (Team or Personal)
  │     ├── Section
  │     │     ├── Task
  │     │     │     ├── Subtask (also a Task)
  │     │     │     ├── Subtask (also a Task)
  │     │     │     └── ...
  │     │     ├── Task
  │     │     └── ...
  │     ├── Section
  │     └── ...
  ├── Project
  ├── Custom Field (Workspace-level definitions)
  └── ...
```

## Resource Types

### Workspace

**Purpose**: Top-level container for an organization or personal workspace.

**Key Fields**:
- `gid` (string): Globally unique identifier
- `name` (string): Workspace name
- `is_organization` (bool): True for org workspaces

**Navigation**:
- **Downward**: → Projects, → Custom Fields, → Users
- **Upward**: (none, top level)

**Example**:
```python
workspace = await client.workspaces.get_workspace(workspace_gid)
projects = await client.projects.get_projects(workspace=workspace_gid)
```

---

### Project

**Purpose**: Collection of related tasks, organized by sections.

**Types**:
- **Team Project**: Shared across team members
- **Personal Project**: Private to individual user

**Key Fields**:
- `gid` (string): Globally unique identifier
- `name` (string): Project name
- `workspace` (dict): Parent workspace
- `team` (dict | null): Team (for team projects)
- `owner` (dict): Project owner

**Navigation**:
- **Downward**: → Sections, → Tasks (direct members), → Custom Field Settings
- **Upward**: ← Workspace

**Example**:
```python
project = await client.projects.get_project(project_gid)
sections = await client.sections.get_sections(project=project_gid)
tasks = await client.tasks.get_tasks(project=project_gid)
```

---

### Section

**Purpose**: Logical grouping within a project (like columns in a Kanban board).

**Key Fields**:
- `gid` (string): Globally unique identifier
- `name` (string): Section name
- `project` (dict): Parent project

**Navigation**:
- **Downward**: → Tasks (members of section)
- **Upward**: ← Project

**Example**:
```python
section = await client.sections.get_section(section_gid)
tasks = await client.tasks.get_tasks(section=section_gid)
```

**Note**: A task can belong to multiple sections in DIFFERENT projects, but only ONE section per project.

---

### Task

**Purpose**: Work item (can be a task or subtask depending on `parent` field).

**Key Fields**:
- `gid` (string): Globally unique identifier
- `name` (string): Task name
- `parent` (dict | null): Parent task (null for top-level tasks)
- `projects` (list[dict]): Projects this task belongs to (multi-homing!)
- `memberships` (list[dict]): Project + section pairs
- `custom_fields` (list[dict]): Custom field values
- `assignee` (dict | null): Assigned user

**Navigation**:
- **Downward**: → Subtasks (children), → Custom Fields, → Attachments
- **Upward**: ← Parent (if subtask), ← Project(s), ← Section(s)

**Example**:
```python
task = await client.tasks.get_task(task_gid)

# Navigate to subtasks
subtasks = await client.tasks.get_subtasks(task_gid)

# Navigate to parent (if subtask)
if task.parent:
    parent = await client.tasks.get_task(task.parent["gid"])

# Navigate to projects (multi-homing)
for project_ref in task.projects:
    project = await client.projects.get_project(project_ref["gid"])
```

---

### Subtask

**Definition**: A subtask is simply a **Task with a `parent` field set**.

**Key Insight**: Subtasks are NOT a separate resource type—they're Tasks that reference a parent Task.

**Navigation**:
- **Upward**: ← Parent Task (via `parent.gid`)
- **Lateral**: ← Siblings (other subtasks of same parent)

**Example**:
```python
# Creating a subtask
subtask = await client.tasks.create_task({
    "name": "Subtask Name",
    "parent": parent_task_gid,  # This makes it a subtask
})

# A subtask can itself have subtasks (nested hierarchy)
nested_subtask = await client.tasks.create_task({
    "name": "Nested Subtask",
    "parent": subtask.gid,
})
```

**Depth Limit**: Asana supports arbitrary depth of subtask nesting.

---

## Multi-Homing

### Key Concept

**Tasks can belong to MULTIPLE projects simultaneously.**

This is called **multi-homing** and is a critical Asana feature that differs from traditional hierarchical systems.

### Memberships

A task's `memberships` field tracks all project+section pairs:

```python
task.memberships = [
    {"project": {"gid": "proj1"}, "section": {"gid": "sec1"}},
    {"project": {"gid": "proj2"}, "section": {"gid": "sec2"}},
]
```

### Implications for SDK Usage

**Business Model Convention**: Business entities (Business, Contact, Unit) typically belong to ONE primary project defined by `PRIMARY_PROJECT_GID`.

**Detection**: Multi-homing is why Tier 1 detection checks project membership (see [REF-detection-tiers.md](./REF-detection-tiers.md)).

**Healing**: When adding tasks to primary project, ensure not to remove existing memberships unless intentional.

**Example**:
```python
# Add task to additional project (multi-home)
await client.tasks.add_project(
    task_gid=task.gid,
    project=additional_project_gid,
    section=section_gid,  # Optional
)

# Remove from project
await client.tasks.remove_project(
    task_gid=task.gid,
    project=project_to_remove_gid,
)
```

---

## Navigation Patterns

### Downward Navigation (Container → Contents)

```python
# Workspace → Projects
workspace_gid = "123"
projects = await client.projects.get_projects(workspace=workspace_gid)

# Project → Sections
project_gid = "456"
sections = await client.sections.get_sections(project=project_gid)

# Section → Tasks
section_gid = "789"
tasks = await client.tasks.get_tasks(section=section_gid)

# Task → Subtasks
task_gid = "999"
subtasks = await client.tasks.get_subtasks(task_gid)
```

### Upward Navigation (Contents → Container)

```python
# Task → Parent Task
task = await client.tasks.get_task(task_gid)
if task.parent:
    parent = await client.tasks.get_task(task.parent["gid"])

# Task → Projects (multi-homing aware)
for project_ref in task.projects:
    project = await client.projects.get_project(project_ref["gid"])

# Section → Project
section = await client.sections.get_section(section_gid)
project = await client.projects.get_project(section.project["gid"])
```

### Lateral Navigation (Siblings)

```python
# Get sibling subtasks (same parent)
task = await client.tasks.get_task(task_gid)
if task.parent:
    all_subtasks = await client.tasks.get_subtasks(task.parent["gid"])
    siblings = [t for t in all_subtasks if t.gid != task.gid]

# Get tasks in same section
section_tasks = await client.tasks.get_tasks(section=section_gid)
```

---

## Custom Fields

### Workspace-Level Definitions

Custom fields are **defined at the workspace level** but **valued at the task level**.

**Definition**:
```python
# Custom field defined in workspace
custom_field = {
    "gid": "cf_123",
    "name": "Status",
    "resource_type": "custom_field",
    "type": "enum",
    "enum_options": [
        {"gid": "eo_1", "name": "Active", "enabled": True},
        {"gid": "eo_2", "name": "Inactive", "enabled": True},
    ]
}
```

**Value on Task**:
```python
# Task has custom field value
task.custom_fields = [
    {
        "gid": "cf_123",
        "name": "Status",
        "type": "enum",
        "enum_value": {"gid": "eo_1", "name": "Active"}
    }
]
```

### Project Custom Field Settings

Projects can specify which workspace custom fields are displayed and their order:

```python
project.custom_field_settings = [
    {
        "gid": "cfs_1",
        "custom_field": {"gid": "cf_123", "name": "Status"},
        "is_important": True,
    }
]
```

---

## SDK Implementation

### Business Model Hierarchy

The autom8_asana SDK extends Asana's hierarchy with **business entities** (Business, Contact, Unit, Offer):

```
Business (Task in primary project)
  ├── ContactHolder (Subtask section)
  │     ├── Contact (Subtask)
  │     └── Contact (Subtask)
  ├── UnitHolder (Subtask section)
  │     ├── Unit (Subtask)
  │     │     ├── OfferHolder (Nested subtask section)
  │     │     │     └── Offer (Subtask)
  │     │     └── ProcessHolder (Nested subtask section)
  │     │           └── Process (Subtask)
  │     └── Unit (Subtask)
  └── LocationHolder (Subtask section)
        └── Location (Subtask)
```

**Mapping to Asana Hierarchy**:
- **Business** = Task in primary project
- **Holders** (ContactHolder, UnitHolder) = Subtasks with specific names ("Contacts", "Units")
- **Child Entities** (Contact, Unit) = Subtasks of holder subtasks

**References**:
- [REF-entity-lifecycle.md](./REF-entity-lifecycle.md)
- [TDD-0027: Business Model Architecture](../design/TDD-0027-business-model-architecture.md)

---

## Common Patterns

### Pattern: Traverse Entire Workspace

```python
workspace = await client.workspaces.get_workspace(workspace_gid)
projects = await client.projects.get_projects(workspace=workspace_gid)

for project in projects:
    sections = await client.sections.get_sections(project=project.gid)

    for section in sections:
        tasks = await client.tasks.get_tasks(section=section.gid)

        for task in tasks:
            # Process task
            print(f"Task: {task.name}")
```

### Pattern: Find Primary Project for Task

```python
task = await client.tasks.get_task(task_gid)

# Check all memberships for primary project
primary_project_gid = Business.PRIMARY_PROJECT_GID

for membership in task.memberships:
    if membership["project"]["gid"] == primary_project_gid:
        print("Task belongs to primary project")
        break
```

---

## See Also

- [REF-entity-lifecycle.md](./REF-entity-lifecycle.md) - Entity lifecycle (uses hierarchy navigation)
- [REF-detection-tiers.md](./REF-detection-tiers.md) - Detection Tier 1 uses project membership
- [TDD-0027: Business Model Architecture](../design/TDD-0027-business-model-architecture.md)
