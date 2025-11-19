from typing import Dict, Any, List
from loguru import logger

from .base_processor import BaseHarborWebhookProcessor


class ProjectWebhookProcessor(BaseHarborWebhookProcessor):
    """Handles Harbor project webhook events."""
    
    async def _process_event(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        event_type = event_data.get("type", "")
        
        if "DELETE_PROJECT" in event_type:
            return await self._handle_project_delete(event_data)
        
        logger.debug(f"Unhandled project event type: {event_type}")
        return []
            
    async def _handle_project_delete(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle project delete events."""
        # For delete events, Ocean will handle entity removal automatically
        # when the entity is no longer returned by the resync
        logger.info("Project delete event received - entity will be removed on next resync")
        return []