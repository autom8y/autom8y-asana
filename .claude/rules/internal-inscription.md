---
paths:
  - "internal/inscription/**"
---

When modifying files in internal/inscription/:
- 3 owner types: knossos (always overwritten), satellite (never overwritten), regenerate (from source)
- Marker format: <!-- KNOSSOS:START region-name --> ... <!-- KNOSSOS:END region-name -->
- Region names are kebab-case; options are key=value pairs on the START marker
- Pipeline: LoadManifest -> Generate -> Merge -> Backup -> Write -> UpdateHashes
- Merge preserves satellite regions and detects conflicts via SHA256 hash comparison
- KNOSSOS_MANIFEST.yaml tracks region ownership, hashes, and inscription version
- Atomic file writes via AtomicWriteFile() to prevent corruption on interrupted sync
