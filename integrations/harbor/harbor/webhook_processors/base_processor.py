from typing import Dict, Any, List
from abc import ABC, abstractmethod
import hashlib
import hmac
from loguru import logger
from port_ocean.core.handlers.webhook.webhook_event import WebhookEvent
from port_ocean.core.handlers.webhook.webhook_event import WebhookEventRawResults
from port_ocean.context.ocean import ocean

from harbor.clients.harbor_client import HarborClient


class BaseHarborWebhookProcessor(ABC):
    def __init__(self):
        self.client = self._create_harbor_client()
        
    def _create_harbor_client(self) -> HarborClient:
        config = ocean.integration_config
        return HarborClient(
            base_url=config.get("harborUrl"),
            username=config.get("harborUsername"),
            password=config.get("harborPassword")
        )
        
    def _validate_webhook_signature(self, body: bytes, signature: str, secret: str) -> bool:
        if not secret or not signature:
            return True
            
        expected = hmac.new(
            secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if signature.startswith("sha256="):
            signature = signature[7:]
            
        return hmac.compare_digest(expected, signature)
        
    async def process(self, webhook_event: WebhookEvent) -> WebhookEventRawResults:
        try:
            event_data = webhook_event.body_json
            
            webhook_secret = ocean.integration_config.get("webhookSecret")
            if webhook_secret:
                signature = webhook_event.headers.get("x-harbor-signature", "")
                if not self._validate_webhook_signature(webhook_event.body, signature, webhook_secret):
                    logger.warning("Invalid webhook signature")
                    return WebhookEventRawResults([])
            
            logger.info(f"Processing Harbor webhook: {event_data.get('type', 'unknown')}")
            results = await self._process_event(event_data)
            return WebhookEventRawResults(results)
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return WebhookEventRawResults([])
            
    @abstractmethod
    async def _process_event(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass