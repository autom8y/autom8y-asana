---
type: review
status: closed
clerk_start_row: 19824
tom_word: e680cb018e71
kit: 72852c68402c
---

# Fleet identity kit v1.1 receipt: MATCH

- Stamped 2026-11-01T21:46:52Z (date -u). Run once at 21:46:43Z on the clerk START row 19824, inside the window; no retry, no other AWS call.
- Seat autom8y-asana-ef. Census SET (DIRENV_DIR, DIRENV_FILE presence only); direnv hook defined, not wired.
- Kit re-hashed before the run: 72852c68402c (full sha matched). Run from the kit directory as `bash KIT-fleet-identity-v1.1.sh 7b369e3ed9d5`.
- **Profile form: AMBIENT.** The seat set no AWS_PROFILE, matching every AWS read this seat ran today; the inherited environment was not inspected.

```
TYPE=assumed-role h12=7b369e3ed9d5
rc=0
```

Result: **MATCH** with the expected h12 7b369e3ed9d5 (hex, not all digits, so not split).
