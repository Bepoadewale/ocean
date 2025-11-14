from typing import Dict, Any, List
from abc import ABC, abstractmethod
import time
from loguru import logger
from port_ocean.core.handlers.webhook.abstract_webhook_processor import AbstractWebhookProcessor
from port_ocean.core.handlers.webhook.webhook_event import WebhookEvent
from port_ocean.context.ocean import ocean

from harbor.clients.harbor_client import HarborClient
from harbor.helpers.webhook_utils import validate_webhook_signature, extract_resource_info
from harbor.helpers.metrics import WebhookMetrics


class BaseHarborWebhookProcessor(AbstractWebhookProcessor, ABC):
    """Base class for Harbor webhook processors."""
    
    def __init__(self):
        super().__init__()
        self.client = self._create_harbor_client()
        
    def _create_harbor_client(self) -> HarborClient:
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
        
    async def process(self, webhook_event: WebhookEvent) -> List[Dict[str, Any]]:
        try:
            event_data = webhook_event.body_json
            resource_info = extract_resource_info(event_data)
            event_type = resource_info['event_type']
            
            # Validate signature if secret is configured
            webhook_secret = getattr(ocean.integration_config, 'webhook_secret', None)
            if webhook_secret:
                signature = webhook_event.headers.get("x-harbor-signature", "")
                if not validate_webhook_signature(webhook_event.body, signature, webhook_secret):
                    logger.warning(f"Invalid webhook signature for {event_type}")
                    return []
            
            logger.info(f"Processing {event_type} webhook")
            return await self._process_event(event_data, resource_info)
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return []
            
    @abstractmethod
    async def _process_event(self, event_data: Dict[str, Any], resource_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process the specific Harbor event. Must be implemented by subclasses."""
        pass