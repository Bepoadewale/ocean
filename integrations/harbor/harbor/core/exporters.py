from typing import AsyncGenerator, List, Dict, Any
import asyncio
from loguru import logger
from port_ocean.utils.cache import cache_iterator_result
from harbor.clients.harbor_client import HarborClient
from harbor.helpers.metrics import IngestionStats


class BaseExporter:
    def __init__(self, client: HarborClient):
        self.client = client
        self.stats = IngestionStats()
        
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Base method for paginated resource fetching with filtering support."""
        raise NotImplementedError("Subclasses must implement get_paginated_resources")


class ProjectExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        logger.info("Starting Harbor projects export")
        filters = selector or {}
        
        try:
            async for projects_batch in self.client.get_paginated_projects(**filters):
                self.stats.projects_processed += len(projects_batch)
                logger.info(f"Yielding {len(projects_batch)} projects (total: {self.stats.projects_processed})")
                yield projects_batch
        except Exception as e:
            self.stats.projects_errors += 1
            logger.error(f"Error in projects export: {e}")
            raise
        finally:
            logger.info(f"Projects export completed: {self.stats.projects_processed} processed, {self.stats.projects_errors} errors")


class UserExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        logger.info("Starting Harbor users export")
        filters = selector or {}
        
        try:
            async for users_batch in self.client.get_paginated_users(**filters):
                self.stats.users_processed += len(users_batch)
                logger.info(f"Yielding {len(users_batch)} users (total: {self.stats.users_processed})")
                yield users_batch
        except Exception as e:
            self.stats.users_errors += 1
            logger.error(f"Error in users export: {e}")
            raise
        finally:
            logger.info(f"Users export completed: {self.stats.users_processed} processed, {self.stats.users_errors} errors")


class RepositoryExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        filters = selector or {}
        project_name = filters.get("project_name")
        
        if project_name:
            async for repos_batch in self._fetch_project_repositories(project_name, filters):
                yield repos_batch
        else:
            async for projects_batch in self.client.get_paginated_projects():
                tasks = [self._fetch_project_repositories(p["name"], filters) for p in projects_batch[:5]]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Repository fetch failed: {result}")
                        continue
                    async for repos_batch in result:
                        yield repos_batch
                    
    async def _fetch_project_repositories(self, project_name: str, filters: Dict[str, Any]) -> AsyncGenerator[List[Dict[str, Any]], None]:
        async for repos_batch in self.client.get_paginated_repositories(project_name, **filters):
            for repo in repos_batch:
                repo["project_name"] = project_name
            yield repos_batch


class ArtifactExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        filters = selector or {}
        project_name = filters.get("project_name")
        repository_name = filters.get("repository_name")
        
        if project_name and repository_name:
            async for artifacts_batch in self._fetch_repository_artifacts(
                {"name": repository_name, "project_name": project_name}, filters
            ):
                yield artifacts_batch
        else:
            repo_exporter = RepositoryExporter(self.client)
            repo_filters = {k: v for k, v in filters.items() if k == "project_name"}
            
            async for repos_batch in repo_exporter.get_paginated_resources(repo_filters):
                tasks = [self._fetch_repository_artifacts(repo, filters) for repo in repos_batch[:3]]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Artifact fetch failed: {result}")
                        continue
                    async for artifacts_batch in result:
                        yield artifacts_batch
                    
    async def _fetch_repository_artifacts(self, repo: Dict[str, Any], filters: Dict[str, Any]) -> AsyncGenerator[List[Dict[str, Any]], None]:
        project_name = repo["project_name"]
        repo_name = repo["name"].split("/")[-1]
        
        try:
            artifact_filters = {k: v for k, v in filters.items() 
                              if k in ["tag_pattern", "created_since", "media_type", 
                                      "with_scan_results", "min_severity", "max_size_mb"]}
            
            async for artifacts_batch in self.client.get_paginated_artifacts(project_name, repo_name, **artifact_filters):
                for artifact in artifacts_batch:
                    artifact.update({
                        "project_name": project_name,
                        "repository_name": repo_name
                    })
                yield artifacts_batch
        except Exception as e:
            logger.warning(f"Failed to fetch artifacts for {project_name}/{repo_name}: {e}")
            return