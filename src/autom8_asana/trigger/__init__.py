"""D6 trigger package: the Asana webhook shadow receiver and its decision path.

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 section 2. The modules
named there (registration, signature, hook_store, hook_registry, ports, sweeper,
resolver_adapter, decision engine) land in later PRs. Their import boundaries are
declared as import-linter contracts in ``pyproject.toml`` and run in CI by
``tests/arch/test_import_contracts.py``. Two contracts are live: AWS imports only in the
stores, and no import path to a token-mint client. The other two are pending until their
modules land. The runtime class check on each adapter's client is not in place yet; it
lands with the adapters in A2 (registration) and A3 (receiver).

This module intentionally holds no code.
"""
