---
schema_version: "2.0"
sprint_id: sprint-service-key-dx-20260108
session_id: session-20260107-180258-f44cd3cb
status: pending
created_at: "2026-01-08T16:04:45Z"
started_at: null
completed_at: null
---

# Sprint: Service Key Management DX Tooling

## Goal
Add `revoke` CLI command to service_key_manager.py and wire into justfile ecosystem.

## Context
This sprint implements the revoke functionality for service keys, providing CLI and justfile integration to complete the service key management tooling DX improvements. The work is structured in phases corresponding to the implementation layers: CLI interface, domain logic, output formatting, local development support, and justfile integration.

## Tasks

### TASK-001: Add revoke subparser to CLI (Phase 1.1)
- **Phase**: implementation
- **Status**: pending
- **Agent**: principal-engineer
- **Dependencies**: []
- **Description**: Add argparse subparser for `revoke` command with required --key-id argument
- **Acceptance Criteria**:
  - Subparser accepts --key-id argument
  - Help text matches existing patterns
  - Argument validation in place

### TASK-002: Add revoke_service_key domain function (Phase 1.2)
- **Phase**: implementation
- **Status**: pending
- **Agent**: principal-engineer
- **Dependencies**: []
- **Description**: Implement domain function in service_key_manager.py to call Secrets Manager revoke API
- **Acceptance Criteria**:
  - Function follows existing domain function patterns
  - Proper error handling for AWS API calls
  - Returns structured result for handler consumption

### TASK-003: Add handle_revoke handler function (Phase 1.3)
- **Phase**: implementation
- **Status**: pending
- **Agent**: principal-engineer
- **Dependencies**: [TASK-001, TASK-002]
- **Description**: Implement handler function that coordinates revoke operation and output formatting
- **Acceptance Criteria**:
  - Handler follows existing handler patterns
  - Proper error handling and logging
  - Integrates with OutputFormatter

### TASK-004: Add format_key_revoked to OutputFormatter (Phase 1.4)
- **Phase**: implementation
- **Status**: pending
- **Agent**: principal-engineer
- **Dependencies**: []
- **Description**: Add formatting method to OutputFormatter for revoke operation results
- **Acceptance Criteria**:
  - Consistent with existing formatter methods
  - Supports both human-readable and JSON output
  - Clear success/failure messaging

### TASK-005: Add routing in main() (Phase 1.5)
- **Phase**: implementation
- **Status**: pending
- **Agent**: principal-engineer
- **Dependencies**: [TASK-003]
- **Description**: Wire revoke subcommand into main() routing logic
- **Acceptance Criteria**:
  - Consistent with existing routing patterns
  - Proper command dispatch
  - Error handling in place

### TASK-006: Add _revoke_service_key_via_db for local dev (Phase 3)
- **Phase**: implementation
- **Status**: pending
- **Agent**: principal-engineer
- **Dependencies**: [TASK-002]
- **Description**: Implement local development variant that updates cache directly via database
- **Acceptance Criteria**:
  - Follows existing local dev patterns (_create_service_key_via_db)
  - Updates cache_metadata table appropriately
  - Proper error handling

### TASK-007: Add justfile tasks to auth.just (Phase 2)
- **Phase**: implementation
- **Status**: pending
- **Agent**: principal-engineer
- **Dependencies**: [TASK-005, TASK-006]
- **Description**: Add revoke recipes to justfile with both AWS and local variants
- **Acceptance Criteria**:
  - Consistent with existing justfile patterns
  - Both cloud and local variants implemented
  - Proper parameter validation and help text

### TASK-008: QA validation and testing
- **Phase**: qa
- **Status**: pending
- **Agent**: qa-adversary
- **Dependencies**: [TASK-007]
- **Description**: Validate end-to-end functionality of revoke command in both AWS and local modes
- **Acceptance Criteria**:
  - CLI command works as expected
  - Justfile integration validated
  - Both cloud and local modes tested
  - Error handling validated
  - Output formatting correct

## Dependencies
- All implementation tasks (TASK-001 through TASK-007) must complete before QA
- TASK-003 depends on TASK-001 and TASK-002
- TASK-005 depends on TASK-003
- TASK-006 depends on TASK-002
- TASK-007 depends on TASK-005 and TASK-006

## Blockers
None.

## Artifacts
- Implementation: scripts/service_key_manager.py (modifications)
- Implementation: justfiles/auth.just (modifications)
- QA Report: docs/test-plans/QA-REPORT-service-key-dx-tooling.md

## Notes
This sprint completes the service key management DX tooling by adding revoke capability alongside the existing create and list operations. The implementation follows established patterns from the create operation for consistency.
