---
artifact_id: {artifact_id}
title: {title}
type: debt-ledger
created_at: {created_at}
author: {author}
status: {status:draft}
schema_version: "1.0"

scope:
  directories:
    - {directory_1}
    # Add more as needed
  categories:
    - {category_1}
    # Valid: code, doc, test, infra, design
  exclusions:
    - {exclusion_1:none}
    # Add patterns to exclude

statistics:
  total_items: {total_items}
  by_category:
    code: {code_count:0}
    doc: {doc_count:0}
    test: {test_count:0}
    infra: {infra_count:0}
    design: {design_count:0}
  by_type:
    {type_name}: {type_count}
    # Add breakdown by specific types

[{session_id: {session_id}}]
[{initiative: {initiative}}]
[{previous_ledger: {previous_ledger}}]
---

# {title}

<!-- TEMPLATE GUIDANCE: Replace all {placeholders} with actual values.
     Remove optional sections [{...}] if not needed.
     Strip this comment and all <!-- --> comments in final artifact.
-->

## Executive Summary

<!-- Provide 2-3 sentence overview of debt audit findings -->

{executive_summary}

## Audit Scope

**Directories Audited:**
- {directory_list}

**Categories Included:**
- {category_list}

**Exclusions:**
[{exclusion_list}]

**Audit Date:** {created_at}

## Debt Inventory

<!-- Organize items by category. Use consistent ID format (C001, D001, etc.) -->

### Code Debt

<!-- category: code -->

| ID | Location | Type | Description | [{Age}] | [{Owner}] |
|----|----------|------|-------------|---------|-----------|
| {item_id} | {location} | {type} | {description} | [{age}] | [{owner}] |

**Evidence:**
```
{evidence_snippet}
```

[{Related Items: {related_ids}}]

### Documentation Debt

<!-- category: doc -->

| ID | Location | Type | Description | [{Age}] | [{Owner}] |
|----|----------|------|-------------|---------|-----------|
| {item_id} | {location} | {type} | {description} | [{age}] | [{owner}] |

### Test Debt

<!-- category: test -->

| ID | Location | Type | Description | [{Age}] | [{Owner}] |
|----|----------|------|-------------|---------|-----------|
| {item_id} | {location} | {type} | {description} | [{age}] | [{owner}] |

### Infrastructure Debt

<!-- category: infra -->

| ID | Location | Type | Description | [{Age}] | [{Owner}] |
|----|----------|------|-------------|---------|-----------|
| {item_id} | {location} | {type} | {description} | [{age}] | [{owner}] |

### Design Debt

<!-- category: design -->

| ID | Location | Type | Description | [{Age}] | [{Owner}] |
|----|----------|------|-------------|---------|-----------|
| {item_id} | {location} | {type} | {description} | [{age}] | [{owner}] |

## Summary Statistics

**Total Items:** {total_items}

**By Category:**
- Code: {code_count}
- Documentation: {doc_count}
- Test: {test_count}
- Infrastructure: {infra_count}
- Design: {design_count}

**By Type:**
- {type_name}: {type_count}
- {type_name}: {type_count}
<!-- Add all specific types found -->

## Audit Limitations

<!-- Document known gaps, incomplete areas, or caveats -->

{audit_limitations}

[{## Debt Diff

<!-- OPTIONAL: Include when previous_ledger is specified -->

**Baseline:** {previous_ledger}

**Changes Since Baseline:**
- Added: {added_count} items
- Resolved: {resolved_count} items
- Modified: {modified_count} items

**Net Change:** {net_change}

### New Items

{new_items_list}

### Resolved Items

{resolved_items_list}
}]

[{## Ownership Report

<!-- OPTIONAL: Include when ownership data is available -->

**By Owner:**

### {owner_name}

- {item_id}: {description}
- {item_id}: {description}

### Unassigned

- {item_id}: {description}
}]
