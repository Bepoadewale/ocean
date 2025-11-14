from port_ocean.context.ocean import ocean
from port_ocean.core.ocean_types import ASYNC_GENERATOR_RESYNC_TYPE
from loguru import logger

from harbor.clients.harbor_client import HarborClient
from harbor.core.exporters import ProjectExporter, UserExporter, RepositoryExporter, ArtifactExporter
from harbor.webhook_processors import ArtifactWebhookProcessor, RepositoryWebhookProcessor, ProjectWebhookProcessor


def create_harbor_client() -> HarborClient:
    """Create Harbor client from configuration."""
    config = ocean.integration_config
    return HarborClient(
        base_url=config.harbor_url,
        username=config.username,
        password=config.password,
        max_concurrent_requests=config.max_concurrent_requests,
        request_timeout=config.request_timeout,
        rate_limit_delay=config.rate_limit_delay,
        verify_ssl=config.verify_ssl
    )


def get_selector_config(kind: str) -> dict:
    """Extract selector configuration for a specific resource kind."""
    config = ocean.integration_config
    
    for resource in config.resources:
        if resource.kind == kind:
            return resource.selector.dict(exclude_unset=True)
    
    return {}


@ocean.on_resync("harbor-project")
async def resync_projects(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    """Resync all projects from Harbor."""
    logger.info("Starting Harbor projects resync")
    
    client = create_harbor_client()
    exporter = ProjectExporter(client)
    selector = get_selector_config("harbor-project")
    
    logger.info(f"Using project selector: {selector}")
    
    async for projects_batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding projects batch of size: {len(projects_batch)}")
        yield projects_batch


@ocean.on_resync("harbor-user")
async def resync_users(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    """Resync all users from Harbor."""
    logger.info("Starting Harbor users resync")
    
    client = create_harbor_client()
    exporter = UserExporter(client)
    selector = get_selector_config("harbor-user")
    
    logger.info(f"Using user selector: {selector}")
    
    async for users_batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding users batch of size: {len(users_batch)}")
        yield users_batch


@ocean.on_resync("harbor-repository")
async def resync_repositories(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    """Resync all repositories from Harbor."""
    logger.info("Starting Harbor repositories resync")
    
    client = create_harbor_client()
    exporter = RepositoryExporter(client)
    selector = get_selector_config("harbor-repository")
    
    logger.info(f"Using repository selector: {selector}")
    
    async for repositories_batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding repositories batch of size: {len(repositories_batch)}")
        yield repositories_batch


@ocean.on_resync("harbor-artifact")
async def resync_artifacts(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    """Resync all artifacts from Harbor."""
    logger.info("Starting Harbor artifacts resync")
    
    client = create_harbor_client()
    exporter = ArtifactExporter(client)
    selector = get_selector_config("harbor-artifact")
    
    logger.info(f"Using artifact selector: {selector}")
    
    async for artifacts_batch in exporter.get_paginated_resources(selector):
        logger.info(f"Yielding artifacts batch of size: {len(artifacts_batch)}")
        yield artifacts_batch


# Register webhook processors
@ocean.router.post("/webhooks/artifacts")
async def handle_artifact_webhooks(request):
    """Handle Harbor artifact webhook events."""
    processor = ArtifactWebhookProcessor()
    return await processor.process(request)


@ocean.router.post("/webhooks/repositories")
async def handle_repository_webhooks(request):
    """Handle Harbor repository webhook events."""
    processor = RepositoryWebhookProcessor()
    return await processor.process(request)


@ocean.router.post("/webhooks/projects")
async def handle_project_webhooks(request):
    """Handle Harbor project webhook events."""
    processor = ProjectWebhookProcessor()
    return await processor.process(request)


@ocean.router.post("/webhooks/harbor")
async def handle_harbor_webhooks(request):
    """Handle all Harbor webhook events on a single endpoint."""
    # Route to appropriate processor based on event type
    body = await request.json()
    event_type = body.get("type", "")
    
    if "PUSH_ARTIFACT" in event_type or "DELETE_ARTIFACT" in event_type:
        processor = ArtifactWebhookProcessor()
    elif "DELETE_REPOSITORY" in event_type:
        processor = RepositoryWebhookProcessor()
    else:
        processor = ProjectWebhookProcessor()
    
    return await processor.process(request)