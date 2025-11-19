from typing import AsyncGenerator, List, Dict, Any
import asyncio
from loguru import logger
from port_ocean.utils.cache import cache_iterator_result
from harbor.clients.harbor_client import HarborClient


class BaseExporter:
    def __init__(self, client: HarborClient):
        self.client = client
        
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        raise NotImplementedError("Subclasses must implement get_paginated_resources")


class ProjectExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        logger.info("Starting Harbor projects export")
        filters = selector or {}
        
        page = 1
        while True:
            projects = await self.client.get_projects(page=page, **filters)
            if not projects:
                break
            
            projects.sort(key=lambda x: (x.get("creation_time", ""), x.get("name", "")))
            logger.info(f"Yielding {len(projects)} projects")
            yield projects
            
            if len(projects) < 100:
                break
            page += 1


class UserExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        logger.info("Starting Harbor users export")
        filters = selector or {}
        
        page = 1
        while True:
            users = await self.client.get_users(page=page, **filters)
            if not users:
                break
            
            # Sort for deterministic ordering
            users.sort(key=lambda x: (x.get("creation_time", ""), x.get("username", "")))
            logger.info(f"Yielding {len(users)} users")
            yield users
            
            if len(users) < 100:
                break
            page += 1


class RepositoryExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        logger.info("Starting Harbor repositories export")
        filters = selector or {}
        project_name = filters.get("project_name")
        
        if project_name:
            # Export repositories for specific project
            page = 1
            while True:
                repos = await self.client.get_repositories(project_name, page=page, **filters)
                if not repos:
                    break
                
                for repo in repos:
                    repo["project_name"] = project_name
                
                repos.sort(key=lambda x: (x.get("creation_time", ""), x.get("name", "")))
                logger.info(f"Yielding {len(repos)} repositories for project {project_name}")
                yield repos
                
                if len(repos) < 100:
                    break
                page += 1
        else:
            # Export repositories for all projects
            all_projects = []
            page = 1
            while True:
                projects = await self.client.get_projects(page=page)
                if not projects:
                    break
                all_projects.extend(projects)
                if len(projects) < 100:
                    break
                page += 1
            
            # Process projects with concurrency
            semaphore = asyncio.Semaphore(5)
            
            async def process_project(project):
                async with semaphore:
                    project_repos = []
                    try:
                        page = 1
                        while True:
                            repos = await self.client.get_repositories(project["name"], page=page, **filters)
                            if not repos:
                                break
                            for repo in repos:
                                repo["project_name"] = project["name"]
                            project_repos.extend(repos)
                            if len(repos) < 100:
                                break
                            page += 1
                    except Exception as e:
                        logger.warning(f"Failed to fetch repositories for project {project['name']}: {e}")
                    return project_repos
            
            # Process projects in batches
            batch_size = 10
            for i in range(0, len(all_projects), batch_size):
                project_batch = all_projects[i:i + batch_size]
                tasks = [process_project(project) for project in project_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                all_repos = []
                for result in results:
                    if isinstance(result, list):
                        all_repos.extend(result)
                
                if all_repos:
                    all_repos.sort(key=lambda x: (x.get("creation_time", ""), x.get("name", "")))
                    logger.info(f"Yielding {len(all_repos)} repositories from batch")
                    yield all_repos


class ArtifactExporter(BaseExporter):
    @cache_iterator_result()
    async def get_paginated_resources(self, selector: Dict[str, Any] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        logger.info("Starting Harbor artifacts export")
        filters = selector or {}
        project_name = filters.get("project_name")
        repository_name = filters.get("repository_name")
        
        artifact_filters = {k: v for k, v in filters.items() 
                          if k in ["tag_pattern", "created_since", "media_type", 
                                  "with_scan_results", "min_severity", "max_size_mb"]}
        
        if project_name and repository_name:
            # Export artifacts for specific repository
            page = 1
            while True:
                artifacts = await self.client.get_artifacts(project_name, repository_name, page=page, **artifact_filters)
                if not artifacts:
                    break
                
                for artifact in artifacts:
                    artifact.update({
                        "project_name": project_name,
                        "repository_name": repository_name
                    })
                
                artifacts.sort(key=lambda x: (x.get("push_time", ""), x.get("digest", "")))
                logger.info(f"Yielding {len(artifacts)} artifacts for {project_name}/{repository_name}")
                yield artifacts
                
                if len(artifacts) < 100:
                    break
                page += 1
        else:
            # Export artifacts for all repositories
            all_repo_refs = []
            
            # Get all projects first
            page = 1
            while True:
                projects = await self.client.get_projects(page=page)
                if not projects:
                    break
                
                for project in projects:
                    try:
                        repo_page = 1
                        while True:
                            repos = await self.client.get_repositories(project["name"], page=repo_page)
                            if not repos:
                                break
                            for repo in repos:
                                repo_name = repo["name"].split("/")[-1]
                                all_repo_refs.append((project["name"], repo_name))
                            if len(repos) < 100:
                                break
                            repo_page += 1
                    except Exception as e:
                        logger.warning(f"Failed to fetch repositories for project {project['name']}: {e}")
                
                if len(projects) < 100:
                    break
                page += 1
            
            # Process repositories with concurrency
            semaphore = asyncio.Semaphore(3)
            
            async def process_repository(project_name, repo_name):
                async with semaphore:
                    repo_artifacts = []
                    try:
                        page = 1
                        while True:
                            artifacts = await self.client.get_artifacts(project_name, repo_name, page=page, **artifact_filters)
                            if not artifacts:
                                break
                            for artifact in artifacts:
                                artifact.update({
                                    "project_name": project_name,
                                    "repository_name": repo_name
                                })
                            repo_artifacts.extend(artifacts)
                            if len(artifacts) < 100:
                                break
                            page += 1
                    except Exception as e:
                        logger.warning(f"Failed to fetch artifacts for {project_name}/{repo_name}: {e}")
                    return repo_artifacts
            
            # Process repositories in batches
            batch_size = 5
            for i in range(0, len(all_repo_refs), batch_size):
                repo_batch = all_repo_refs[i:i + batch_size]
                tasks = [process_repository(proj, repo) for proj, repo in repo_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                all_artifacts = []
                for result in results:
                    if isinstance(result, list):
                        all_artifacts.extend(result)
                
                if all_artifacts:
                    all_artifacts.sort(key=lambda x: (x.get("push_time", ""), x.get("digest", "")))
                    logger.info(f"Yielding {len(all_artifacts)} artifacts from batch")
                    yield all_artifacts