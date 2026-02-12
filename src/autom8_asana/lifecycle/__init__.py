"""Lifecycle Engine - Pipeline automation orchestration.

Per TDD-lifecycle-engine: Data-driven lifecycle automation absorbing
PipelineConversionRule behavior.

Entry points:
- LifecycleEngine.handle_transition_async() for transitions
- AutomationDispatch.dispatch_async() for webhook routing
"""

from autom8_asana.lifecycle.completion import (
    CompletionResult,
    CompletionService,
    PipelineAutoCompletionService,
)
from autom8_asana.lifecycle.config import (
    AssigneeConfig,
    CascadingSectionConfig,
    InitActionConfig,
    LifecycleConfig,
    LifecycleConfigModel,
    SeedingConfig,
    SelfLoopConfig,
    StageConfig,
    TransitionConfig,
    ValidationConfig,
    ValidationRuleConfig,
    WiringRuleConfig,
    load_config,
)
from autom8_asana.lifecycle.creation import (
    CreationResult,
    EntityCreationService,
)
from autom8_asana.lifecycle.dispatch import AutomationDispatch
from autom8_asana.lifecycle.engine import LifecycleEngine
from autom8_asana.lifecycle.sections import (
    CascadeResult,
    CascadingSectionService,
)
from autom8_asana.lifecycle.webhook import (
    AsanaWebhookPayload,
    WebhookResponse,
    router,
)
from autom8_asana.lifecycle.wiring import (
    DependencyWiringService,
    WiringResult,
)
from autom8_asana.lifecycle.init_actions import (
    InitActionHandler,
    CommentHandler,
    PlayCreationHandler,
    EntityCreationHandler,
    ProductsCheckHandler,
    CampaignHandler,
    HANDLER_REGISTRY,
)
from autom8_asana.lifecycle.reopen import (
    ReopenResult,
    ReopenService,
)
from autom8_asana.lifecycle.seeding import (
    AutoCascadeSeeder,
    SeedingResult,
)

__all__ = [
    # Configuration
    "LifecycleConfig",
    "LifecycleConfigModel",
    "StageConfig",
    "TransitionConfig",
    "CascadingSectionConfig",
    "InitActionConfig",
    "SelfLoopConfig",
    "WiringRuleConfig",
    "ValidationConfig",
    "ValidationRuleConfig",
    "SeedingConfig",
    "AssigneeConfig",
    "load_config",
    # Services
    "EntityCreationService",
    "CascadingSectionService",
    "PipelineAutoCompletionService",
    "CompletionService",
    "DependencyWiringService",
    "ReopenService",
    "AutoCascadeSeeder",
    # Engine
    "LifecycleEngine",
    "AutomationDispatch",
    # Results
    "CreationResult",
    "CascadeResult",
    "CompletionResult",
    "WiringResult",
    "ReopenResult",
    "SeedingResult",
    # Webhook
    "AsanaWebhookPayload",
    "WebhookResponse",
    "router",
    # Init Action Handlers
    "InitActionHandler",
    "CommentHandler",
    "PlayCreationHandler",
    "EntityCreationHandler",
    "ProductsCheckHandler",
    "CampaignHandler",
    "HANDLER_REGISTRY",
]
