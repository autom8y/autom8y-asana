---
paths:
  - "internal/materialize/**"
---

When modifying files in internal/materialize/:
- Unified pipeline: Sync() dispatches to rite scope (MaterializeWithOptions) then user scope (syncUserScope)
- Scope-gated stages: rite-only stages skip for user scope; user-only stages skip for rite scope
- SyncOptions controls both rite and user scope sync (scope, dry-run, recover, overwrite flags)
- Idempotency invariant: running sync twice must produce identical output
- 4-tier resolution order: rite > dependency > shared > user (rite scope)
- User content is NEVER destroyed (satellite regions, user-agents, user-hooks)
- writeIfChanged() prevents unnecessary file watcher triggers
- MCP merge is union: add/update rite servers, preserve existing satellite servers
- Mena projection strips .dro.md/.lego.md extensions and routes to commands/ or skills/
- Provenance collector is threaded through rite pipeline stages; user scope uses provenance.LoadOrBootstrap
- Volatile infrastructure files (KNOSSOS_MANIFEST.yaml, sync/state.json, ACTIVE_RITE) are NOT tracked in provenance
- Orphan detection: auto-remove knossos-owned by default; --keep-orphans prevents removal
- CollisionChecker reads rite PROVENANCE_MANIFEST.yaml to prevent user scope from shadowing rite resources
- User scope files: user_scope.go (sync logic), collision.go (collision detection), sync_types.go (unified types)
