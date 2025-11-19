from port_ocean.context.ocean import ocean
from port_ocean.core.ocean_types import ASYNC_GENERATOR_RESYNC_TYPE
from loguru import logger

from harbor.clients.harbor_client import HarborClient
from harbor.core.exporters import ProjectExporter, UserExporter, RepositoryExporter, ArtifactExporter
from harbor.webhook_processors import ArtifactWebhookProcessor, RepositoryWebhookProcessor, ProjectWebhookProcessor


def create_harbor_client() -> HarborClient:
    config = ocean.integration_config
    return HarborClient(
        base_url=config["harborUrl"],
        username=config["harborUsername"],
        password=config["harborPassword"]
    )


def get_selector_config(kind: str) -> dict:
    config = ocean.integration_config
    for resource in config.get("resources", []):
        if resource.get("kind") == kind:
            return resource.get("selector", {})
    return {}


@ocean.on_resync("harbor-project")
async def resync_projects(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    logger.info("Starting Harbor projects resync")
    client = create_harbor_client()
    exporter = ProjectExporter(client)
    selector = get_selector_config("harbor-project")
    
    async for batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding projects batch of size: {len(batch)}")
        yield batch


@ocean.on_resync("harbor-user")
async def resync_users(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    logger.info("Starting Harbor users resync")
    client = create_harbor_client()
    exporter = UserExporter(client)
    selector = get_selector_config("harbor-user")
    
    async for batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding users batch of size: {len(batch)}")
        yield batch


@ocean.on_resync("harbor-repository")
async def resync_repositories(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    logger.info("Starting Harbor repositories resync")
    client = create_harbor_client()
    exporter = RepositoryExporter(client)
    selector = get_selector_config("harbor-repository")
    
    async for batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding repositories batch of size: {len(batch)}")
        yield batch


@ocean.on_resync("harbor-artifact")
async def resync_artifacts(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    logger.info("Starting Harbor artifacts resync")
    client = create_harbor_client()
    exporter = ArtifactExporter(client)
    selector = get_selector_config("harbor-artifact")
    
    async for batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding artifacts batch of size: {len(batch)}")
        yield batch


@ocean.router.post("/webhooks/artifacts")
async def handle_artifact_webhooks(request):
    from port_ocean.core.handlers.webhook.webhook_event import WebhookEvent
    return await ArtifactWebhookProcessor().process(WebhookEvent(request))


@ocean.router.post("/webhooks/repositories")
async def handle_repository_webhooks(request):
    from port_ocean.core.handlers.webhook.webhook_event import WebhookEvent
    return await RepositoryWebhookProcessor().process(WebhookEvent(request))


@ocean.router.post("/webhooks/projects")
async def handle_project_webhooks(request):
    from port_ocean.core.handlers.webhook.webhook_event import WebhookEvent
    return await ProjectWebhookProcessor().process(WebhookEvent(request))


@ocean.router.post("/webhooks/harbor")
async def handle_harbor_webhooks(request):
    from port_ocean.core.handlers.webhook.webhook_event import WebhookEvent
    body = await request.json()
    event_type = body.get("type", "")
    
    # Route to appropriate processor based on event type
    if any(x in event_type for x in ["PUSH_ARTIFACT", "DELETE_ARTIFACT", "SCANNING_COMPLETED"]):
        processor = ArtifactWebhookProcessor()
    elif "DELETE_REPOSITORY" in event_type:
        processor = RepositoryWebhookProcessor()
    elif "DELETE_PROJECT" in event_type:
        processor = ProjectWebhookProcessor()
    else:
        processor = ArtifactWebhookProcessor()
    
    return await processor.process(WebhookEvent(request))