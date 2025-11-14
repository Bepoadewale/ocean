from typing import Dict, Any, List
from loguru import logger

from harbor.webhook_processors.base_processor import BaseHarborWebhookProcessor


class ArtifactWebhookProcessor(BaseHarborWebhookProcessor):
    """Handles Harbor artifact webhook events."""
    
    async def _process_event(self, event_data: Dict[str, Any], resource_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        event_type = resource_info['event_type']
        project = resource_info.get('project_name')
        repo = resource_info.get('repository_name')
        digest = resource_info.get('artifact_digest')
        
        if event_type in ["PUSH_ARTIFACT", "SCANNING_COMPLETED"]:
            return await self._upsert_artifact(project, repo, digest)
        elif event_type == "DELETE_ARTIFACT":
            return await self._delete_artifact(project, repo, digest)
        
        return []
            
    async def _upsert_artifact(self, project: str, repo: str, digest: str) -> List[Dict[str, Any]]:
        try:
            artifacts = await self.client.get_artifacts(project, repo, page_size=100)
            artifact = next((a for a in artifacts if a.get('digest') == digest), None) if digest else artifacts[0] if artifacts else None
            
            if not artifact:
                return []
                
            artifact.update({
                'project_name': project,
                'repository_name': repo
            })
            
            return [artifact]
            
        except Exception as e:
            logger.error(f"Failed to fetch artifact: {e}")
            return []
            
    async def _delete_artifact(self, project: str, repo: str, digest: str) -> List[Dict[str, Any]]:
        return []  # Ocean handles deletion when entity is missing