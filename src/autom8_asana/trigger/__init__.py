"""D6 trigger package: the Asana webhook shadow receiver and its decision path.

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 section 2. A2
(registration) landed, DARK:

* ``hook_environment``: the ``ASANA_HOOK_ENVIRONMENT`` marker and the shadow flag.
* ``hook_store``: the one Secrets Manager writer for ``autom8y/asana/webhook-hook/*``.
* ``hook_registry``: the one writer of the D-1 table (registration-side rows).
* ``ports_webhooks``: ``WebhooksClient``, the narrow /webhooks port.
* ``registration``: minting, create, the handshake callable, the leased reconciler.
* ``watched_projects``: AssetEdit and Offer, and the explicit (empty) trigger map.

Nothing in production constructs these yet, and nothing registers a webhook unless
``ASANA_HOOK_SHADOW_ENABLED`` is exactly ``"1"``. The receiver route, signature check,
sweeper and decision engine land in later PRs. Import boundaries are import-linter
contracts in ``pyproject.toml``, run in CI by ``tests/arch/test_import_contracts.py``;
the AsanaClient re-export the graph cannot see is guarded by
``tests/arch/test_trigger_asana_client_ast.py``.

This module intentionally holds no code.
"""
