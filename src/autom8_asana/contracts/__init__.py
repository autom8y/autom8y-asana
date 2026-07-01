"""Cross-repo shared contracts (producer side, SDK-home-ready).

Modules in this package define the typed wire envelopes both autom8y-asana
(producer) and autom8y-data (consumer) build against. They are deliberately
free of autom8y-asana-internal imports so that promotion to ``autom8y-core``
(the established cross-repo model home) is a ``git mv`` + re-export, not a
rewrite.

See ADR-dyn-enum-contract-shared-contract §6 (SDK-home) and the sprint-1
producer TDD-delta D-1 (typed model locus).
"""

from __future__ import annotations
