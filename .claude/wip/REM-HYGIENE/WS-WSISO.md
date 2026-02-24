# WS-WSISO: Workspace Switching Tests

**Objective**: Replace 4 pass-only stubs and 4 tautological constructor-assertion tests in `test_workspace_switching.py` with behavioral workspace isolation tests, or convert to named `pytest.mark.skip` with explicit reasons.

---

## Source Findings

| RS-ID | Finding | Severity | Tests |
|-------|---------|----------|-------|
| RS-012 | 4 test functions with only `pass` as body. Pytest passes them unconditionally. | DEFECT HIGH | lines 166, 193, 227, 255 |
| RS-013 | 4 tests construct model objects and assert same values back. Tests Python assignment, not workspace behavior. | DEFECT HIGH | lines 75, 104, 129, 156-157 |

Related advisory (address if natural):
| RS-014 | Unused `mock_client` assignments at lines 64, 87 | DEFECT HIGH (P2) | 2 lines |

---

## File Targets

- **Test file**: `tests/integration/test_workspace_switching.py`
- **Production source (read only)**:
  - `src/autom8_asana/client.py` (AsanaClient workspace context)
  - `src/autom8_asana/resolution/field_resolver.py` (FieldResolver workspace dependency)
  - `src/autom8_asana/models/business/registry.py` (WorkspaceProjectRegistry)

### Tests to Fix (8 total)

**RS-012 (pass-only stubs)**:
- `test_recommended_pattern_separate_clients` (line 166)
- `test_anti_pattern_switching_workspace_context` (line 193)
- `test_field_name_resolution_workspace_specific` (line 227)
- `test_field_resolver_requires_workspace_context` (line 255)

**RS-013 (tautological assertions)**:
- `test_task_belongs_to_single_workspace` (line 75)
- `test_custom_fields_vary_by_workspace` (line 104)
- `test_team_membership_workspace_specific` (line 129)
- `test_project_scope_is_workspace_scoped` (line 156)

---

## Implementation Strategy

1. **Read production source** to understand what workspace isolation guarantees exist.
2. **If workspace isolation logic exists**: Implement behavioral tests that exercise isolation through the system under test (two clients, two workspaces, verify independence).
3. **If workspace isolation logic does NOT exist**: Convert stubs to named skips:
   ```python
   @pytest.mark.skip(reason="Workspace isolation not yet implemented: <specific contract>")
   def test_recommended_pattern_separate_clients(self):
       pass
   ```
4. **For tautological tests**: Either replace with real behavioral assertions (preferred) or convert to documented skips with specific workspace behavior expectations.
5. **Remove unused mock_client** assignments (RS-014) as part of the cleanup.

---

## Effort Estimate

- **Total**: ~3 hours
- **Risk**: MEDIUM -- workspace isolation contract may not be fully implemented, requiring skip-with-reason instead of full implementation

---

## Dependencies

- None. File has zero overlap with other workstreams.

---

## Rite / Complexity

- **Rite**: 10x-dev (recommended, confirm at dispatch)
- **Complexity**: MODULE
