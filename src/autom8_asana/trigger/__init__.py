"""D6 trigger package: the Asana webhook shadow receiver and its decision path.

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 section 2. The modules
named there (registration, signature, hook_store, hook_registry, ports, sweeper,
resolver_adapter, decision engine) land in later PRs. Their import boundaries are
already enforced by the import-linter contracts in ``pyproject.toml``
(``[tool.importlinter]``), run in CI by ``tests/arch/test_import_contracts.py``.

This module intentionally holds no code.
"""
