from typing import Dict, Any, List
from loguru import logger

from .base_processor import BaseHarborWebhookProcessor


class ArtifactWebhookProcessor(BaseHarborWebhookProcessor):
    """Handles Harbor artifact webhook events."""
    
    async def _process_event(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        event_type = event_data.get("type", "")
        
        if "PUSH_ARTIFACT" in event_type:
            return await self._handle_artifact_push(event_data)
        if "DELETE_ARTIFACT" in event_type:
            return await self._handle_artifact_delete(event_data)
        if "SCANNING_COMPLETED" in event_type:
            return await self._handle_scan_complete(event_data)
        
        logger.debug(f"Unhandled artifact event type: {event_type}")
        return []
            
    async def _handle_artifact_push(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle artifact push events."""
        try:
            event_data_detail = event_data.get("event_data", {})
            repository = event_data_detail.get("repository", {})
            resources = event_data_detail.get("resources", [])
            
            if not repository or not resources:
                logger.warning("Missing repository or resources in artifact push event")
                return []
            
            project_name = repository.get("namespace")
            repo_name = repository.get("name", "").split("/")[-1]
            
            if not project_name or not repo_name:
                logger.warning("Missing project or repository name in event")
                return []
            
            # Fetch updated artifacts
            artifacts = []
            for resource in resources:
                digest = resource.get("digest")
                if digest:
                    try:
                        artifact_list = await self.client.get_artifacts(project_name, repo_name)
                        for artifact in artifact_list:
                            if artifact.get("digest") == digest:
                                artifact.update({
                                    "project_name": project_name,
                                    "repository_name": repo_name
                                })
                                artifacts.append(artifact)
                                break
                    except Exception as e:
                        logger.error(f"Failed to fetch artifact {digest}: {e}")
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to process artifact push event: {e}")
            return []
            
    async def _handle_artifact_delete(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle artifact delete events."""
        # For delete events, Ocean will handle entity removal automatically
        # when the entity is no longer returned by the resync
        logger.info("Artifact delete event received - entity will be removed on next resync")
        return []
            
    async def _handle_scan_complete(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle vulnerability scan completion events."""
        try:
            event_data_detail = event_data.get("event_data", {})
            repository = event_data_detail.get("repository", {})
            resources = event_data_detail.get("resources", [])
            
            project_name = repository.get("namespace")
            repo_name = repository.get("name", "").split("/")[-1]
            
            if not project_name or not repo_name:
                return []
            
            # Fetch artifacts with updated scan results
            artifacts = []
            for resource in resources:
                digest = resource.get("digest")
                if digest:
                    try:
                        artifact_list = await self.client.get_artifacts(
                            project_name, repo_name, with_scan_results=True
                        )
                        for artifact in artifact_list:
                            if artifact.get("digest") == digest:
                                artifact.update({
                                    "project_name": project_name,
                                    "repository_name": repo_name
                                })
                                artifacts.append(artifact)
                                break
                    except Exception as e:
                        logger.error(f"Failed to fetch scanned artifact {digest}: {e}")
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to process scan complete event: {e}")
            return []