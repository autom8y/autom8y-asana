"""Public-API contract for the caller-image plaintext-PAT guard (N2b leg-ii).

The out-of-repo iris/hermes read-route caller consumes
``assert_no_plaintext_pat_in_caller`` as a first-class package export:

    from autom8_asana.auth import assert_no_plaintext_pat_in_caller

The caller MUST invoke it at container startup (before minting the S2S JWT /
calling ``GET /sections``) so a misconfigured caller holding a bare ``ASANA_PAT``
HALTS instead of silently degrading to a plaintext-PAT posture. This test pins
the contract surface so a refactor cannot silently drop the export.
"""

from __future__ import annotations

import autom8_asana.auth as auth
from autom8_asana.auth import assert_no_plaintext_pat_in_caller
from autom8_asana.auth.bot_pat import (
    assert_no_plaintext_pat_in_caller as _canonical,
)


def test_guard_importable_from_package_root() -> None:
    """The guard is importable from the package root and is the canonical object."""
    assert assert_no_plaintext_pat_in_caller is _canonical


def test_guard_declared_in_package_all() -> None:
    """The guard is declared in the package __all__ (explicit public surface)."""
    assert "assert_no_plaintext_pat_in_caller" in auth.__all__
