"""Developer CLI for invoking workflows directly.

Per TDD-ENTITY-SCOPE-001 Section 2.8: Developer CLI for local testing.
Constructs a workflow, calls enumerate_async + execute_async, and
prints the result as JSON.

Usage:
    uv run python scripts/invoke_workflow.py insights-export --gid 123456 --dry-run
    uv run python scripts/invoke_workflow.py conversation-audit --gid 123456
    uv run python scripts/invoke_workflow.py insights-export --gid 123 --gid 456

Or via justfile:
    just invoke insights-export --gid 123456 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Invoke a workflow for specific entities.",
    )
    parser.add_argument(
        "workflow_id",
        help="Workflow ID (e.g., 'insights-export', 'conversation-audit')",
    )
    parser.add_argument(
        "--gid",
        action="append",
        dest="gids",
        help="Entity GID to target (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Skip write operations (upload, delete)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max entities to process",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=None,
        help="Override max_concurrency parameter",
    )
    return parser


def _resolve_config(
    workflow_id: str,
) -> Any:
    """Look up WorkflowHandlerConfig by workflow_id.

    Returns:
        WorkflowHandlerConfig or None if not found.
    """
    configs: dict[str, Any] = {}

    try:
        from autom8_asana.lambda_handlers.insights_export import (
            _config as insights_config,
        )

        configs[insights_config.workflow_id] = insights_config
    except ImportError:
        pass

    try:
        from autom8_asana.lambda_handlers.conversation_audit import (
            _config as audit_config,
        )

        configs[audit_config.workflow_id] = audit_config
    except ImportError:
        pass

    return configs.get(workflow_id)


async def _invoke_direct(args: argparse.Namespace) -> int:
    """Construct workflow directly and invoke.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    from autom8_asana.core.scope import EntityScope

    config = _resolve_config(args.workflow_id)
    if config is None:
        print(
            f"ERROR: Unknown workflow_id '{args.workflow_id}'. "
            f"Available: insights-export, conversation-audit",
            file=sys.stderr,
        )
        return 1

    # Build scope
    scope = EntityScope(
        entity_ids=tuple(args.gids or ()),
        dry_run=args.dry_run,
        limit=args.limit,
    )

    # Build params
    params: dict[str, Any] = {**config.default_params}
    params["workflow_id"] = args.workflow_id
    params.update(scope.to_params())
    if args.max_concurrency is not None:
        params["max_concurrency"] = args.max_concurrency

    # Construct clients and workflow
    from autom8_asana.client import AsanaClient

    asana_client = AsanaClient()

    if config.requires_data_client:
        from autom8_asana.clients.data.client import DataServiceClient

        async with DataServiceClient() as data_client:
            workflow = config.workflow_factory(asana_client, data_client)
            return await _run_workflow(workflow, scope, params)
    else:
        workflow = config.workflow_factory(asana_client, None)
        return await _run_workflow(workflow, scope, params)


async def _run_workflow(workflow: Any, scope: Any, params: dict[str, Any]) -> int:
    """Run validate -> enumerate -> execute and print result.

    Returns:
        Exit code (0 = success, 1 = validation failure).
    """
    validation_errors = await workflow.validate_async()
    if validation_errors:
        print(f"VALIDATION FAILED: {validation_errors}", file=sys.stderr)
        return 1

    entities = await workflow.enumerate_async(scope)
    print(f"Enumerated {len(entities)} entities", file=sys.stderr)

    result = await workflow.execute_async(entities, params)
    print(json.dumps(result.to_response_dict(), indent=2))
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if not args.gids:
        print(
            "ERROR: At least one --gid is required for CLI invocation",
            file=sys.stderr,
        )
        sys.exit(1)

    exit_code = asyncio.run(_invoke_direct(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
