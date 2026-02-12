# Atropos - The Cutter

> What Lachesis measures, Atropos cuts. Every session must end with purpose.

## wrap_session

Completes and archives the active session.

**Syntax**: `wrap_session [--force] [session_id="{id}"]`

**CLI**: `ari session wrap -s "{session_id}" [--force]`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| --force | No | Bypass quality gates |
| session_id | No | Session ID (pass via `-s` flag to CLI) |

**Validation**:
1. Session must be ACTIVE or PARKED
2. Unless --force flag, check for uncommitted changes
3. Unless --force flag, verify quality gates

**Execution**:
1. Call `ari session wrap -s "{session_id}"` (add `--force` if specified; omit `-s` if no session_id)
2. CLI handles lock acquisition and SESSION_CONTEXT.md mutation
3. CLI generates session summary
4. CLI runs quality gate checks (if not --force)
5. CLI generates White Sails confidence signal via `ari sails check`
6. CLI updates session status to ARCHIVED
7. CLI records wrap timestamp and summary
8. Return CLI output

**Quality Gates** (non-force):
- All sprint tasks completed or explicitly deferred
- No uncommitted changes in working tree
- Build passes

**PARKED sessions**: Can be wrapped directly (PARKED -> ARCHIVED is a valid transition). The park reason becomes part of the wrap summary.

**MOIRAI_BYPASS**: Not needed (CLI handles).

**Lock**: CLI handles locking.

---

## generate_sails

Generates the White Sails confidence signal for the session.

**Syntax**: `generate_sails`

**CLI**: `ari sails check`

**Output**: WHITE_SAILS.yaml in session directory

**Color Computation**:
| Condition | Color |
|-----------|-------|
| All proofs pass, no blockers | WHITE |
| Open questions or spike/hotfix | GRAY |
| Proof failures or blockers | BLACK |

**Proof Types**:
- tests: Unit and integration tests pass
- build: Build completes successfully
- lint: Linter passes
- adversarial: Security review (INITIATIVE+ complexity only)
- integration: Cross-satellite testing (INITIATIVE+ complexity only)

**Execution**:
1. Call `ari sails check`
2. CLI evaluates proof gates
3. CLI computes confidence color
4. CLI writes WHITE_SAILS.yaml
5. Return CLI output with color

**MOIRAI_BYPASS**: Not needed (CLI handles).

**Lock**: Not required (read-only analysis).

---

## delete_sprint

Deletes or archives a sprint.

**Syntax**: `delete_sprint sprint_id="{id}" [--archive]`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| sprint_id | Yes | Sprint identifier |
| --archive | No | Archive instead of delete |

**Validation**:
1. Sprint must exist
2. Sprint must not be ACTIVE (park first)
3. If --archive, sprint is preserved in archive; otherwise deleted

**Execution**:
1. If --archive: move SPRINT_CONTEXT.md to session archive directory
2. If delete: remove SPRINT_CONTEXT.md
3. Return success response

**MOIRAI_BYPASS**: Required for SPRINT_CONTEXT.md deletion/move.

**Lock**: Required (context.lock).
