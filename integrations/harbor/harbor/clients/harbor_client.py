from typing import Any, Dict, List, Optional, AsyncGenerator
import base64
import asyncio
import re
from datetime import datetime
from loguru import logger
from port_ocean.context.ocean import ocean


class HarborClient:
    def __init__(self, base_url: str, username: str, password: str, 
                 max_concurrent_requests: int = 10, request_timeout: int = 30,
                 rate_limit_delay: int = 1, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.http_client = ocean.http_client
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.request_timeout = request_timeout
        self.rate_limit_delay = rate_limit_delay
        self.verify_ssl = verify_ssl

    @property
    def headers(self) -> Dict[str, str]:
        auth_string = f"{self.username}:{self.password}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
        return {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v2.0/{endpoint.lstrip('/')}"
        
        async with self.semaphore:
            retries = 0
            max_retries = 3
            
            while retries <= max_retries:
                try:
                    if self.rate_limit_delay > 0:
                        delay = self.rate_limit_delay * (2 ** retries)  # Exponential backoff
                        await asyncio.sleep(delay)
                        
                    response = await self.http_client.get(
                        url, 
                        headers=self.headers, 
                        params=params or {},
                        timeout=self.request_timeout
                    )
                    
                    response.raise_for_status()
                    return response.json()
                    
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Harbor API request failed after {max_retries} retries: {e}")
                        raise
                    logger.warning(f"Harbor API request failed, retrying ({retries}/{max_retries}): {e}")
                    await asyncio.sleep(1 * retries)  # Brief delay before retry

    async def get_projects(
        self, page: int = 1, page_size: int = 100, **filters
    ) -> List[Dict[str, Any]]:
        params = {"page": page, "page_size": page_size}
        
        # Apply Harbor API filters
        if "visibility" in filters:
            params["public"] = filters["visibility"] == "public"
        if "owner" in filters:
            params["owner"] = filters["owner"]
            
        projects = await self._make_request("projects", params)
        
        # Apply client-side filters
        if filters.get("name_prefix"):
            projects = [p for p in projects if p["name"].startswith(filters["name_prefix"])]
        if filters.get("name_regex"):
            pattern = re.compile(filters["name_regex"])
            projects = [p for p in projects if pattern.match(p["name"])]
            
        return projects

    async def get_users(
        self, page: int = 1, page_size: int = 100, **filters
    ) -> List[Dict[str, Any]]:
        params = {"page": page, "page_size": page_size}
        users = await self._make_request("users", params)
        
        # Apply client-side filters
        if filters.get("admin_only"):
            users = [u for u in users if u.get("sysadmin_flag", False)]
        if filters.get("email_domain"):
            domain = filters["email_domain"]
            users = [u for u in users if u.get("email", "").endswith(f"@{domain}")]
            
        return users

    async def get_repositories(
        self, project_name: str, page: int = 1, page_size: int = 100, **filters
    ) -> List[Dict[str, Any]]:
        params = {"page": page, "page_size": page_size}
        repos = await self._make_request(f"projects/{project_name}/repositories", params)
        
        # Apply client-side filters
        if filters.get("name_contains"):
            repos = [r for r in repos if filters["name_contains"] in r["name"]]
        if filters.get("name_starts_with"):
            prefix = filters["name_starts_with"]
            repos = [r for r in repos if r["name"].split("/")[-1].startswith(prefix)]
        if filters.get("min_artifact_count"):
            repos = [r for r in repos if r.get("artifact_count", 0) >= filters["min_artifact_count"]]
        if filters.get("min_pull_count"):
            repos = [r for r in repos if r.get("pull_count", 0) >= filters["min_pull_count"]]
            
        return repos

    async def get_artifacts(
        self, project_name: str, repository_name: str, page: int = 1, page_size: int = 100, **filters
    ) -> List[Dict[str, Any]]:
        params = {"page": page, "page_size": page_size}
        
        # Add scan data if needed
        params["with_scan_overview"] = bool(filters.get("with_scan_results") or filters.get("min_severity"))
            
        repo_encoded = repository_name.replace("/", "%2F")
        artifacts = await self._make_request(
            f"projects/{project_name}/repositories/{repo_encoded}/artifacts", params
        )
        
        # Apply client-side filters
        filtered_artifacts = []
        for artifact in artifacts:
            # Filter by creation date
            if filters.get("created_since"):
                try:
                    created = datetime.fromisoformat(artifact.get("push_time", "").replace("Z", "+00:00"))
                    since = datetime.fromisoformat(filters["created_since"])
                    if created < since:
                        continue
                except (ValueError, TypeError):
                    continue
                    
            # Filter by media type
            if filters.get("media_type") and artifact.get("media_type") != filters["media_type"]:
                continue
                    
            # Filter by size
            if filters.get("max_size_mb"):
                max_bytes = filters["max_size_mb"] * 1024 * 1024
                if artifact.get("size", 0) > max_bytes:
                    continue
                    
            # Filter by tag pattern
            if "tag_pattern" in filters and filters["tag_pattern"]:
                tags = [tag.get("name", "") for tag in artifact.get("tags", [])]
                pattern = re.compile(filters["tag_pattern"])
                if not any(pattern.match(tag) for tag in tags):
                    continue
                    
            # Filter by vulnerability scan results
            if "with_scan_results" in filters and filters["with_scan_results"]:
                scan_overview = artifact.get("scan_overview", {})
                if not scan_overview:
                    continue
                    
            # Filter by minimum severity
            if "min_severity" in filters and filters["min_severity"]:
                scan_overview = artifact.get("scan_overview", {})
                severity_levels = {"negligible": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
                min_level = severity_levels.get(filters["min_severity"], 0)
                
                has_severity = False
                for scanner_name, scan_result in scan_overview.items():
                    summary = scan_result.get("summary", {})
                    for severity, count in summary.items():
                        if severity_levels.get(severity.lower(), 0) >= min_level and count > 0:
                            has_severity = True
                            break
                    if has_severity:
                        break
                        
                if not has_severity:
                    continue
                    
            filtered_artifacts.append(artifact)
            
        return filtered_artifacts

    async def get_paginated_projects(self, **filters) -> AsyncGenerator[List[Dict[str, Any]], None]:
        page = 1
        while True:
            projects = await self.get_projects(page=page, **filters)
            if not projects:
                break
            # Sort for deterministic ordering
            projects.sort(key=lambda x: (x.get("creation_time", ""), x.get("name", "")))
            yield projects
            if len(projects) < 100:  # Last page
                break
            page += 1

    async def get_paginated_users(self, **filters) -> AsyncGenerator[List[Dict[str, Any]], None]:
        page = 1
        while True:
            users = await self.get_users(page=page, **filters)
            if not users:
                break
            # Sort for deterministic ordering
            users.sort(key=lambda x: (x.get("creation_time", ""), x.get("username", "")))
            yield users
            if len(users) < 100:
                break
            page += 1

    async def get_paginated_repositories(
        self, project_name: str, **filters
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        page = 1
        while True:
            repos = await self.get_repositories(project_name, page=page, **filters)
            if not repos:
                break
            # Sort for deterministic ordering
            repos.sort(key=lambda x: (x.get("creation_time", ""), x.get("name", "")))
            yield repos
            if len(repos) < 100:
                break
            page += 1

    async def get_paginated_artifacts(
        self, project_name: str, repository_name: str, **filters
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        page = 1
        while True:
            artifacts = await self.get_artifacts(project_name, repository_name, page=page, **filters)
            if not artifacts:
                break
            # Sort for deterministic ordering
            artifacts.sort(key=lambda x: (x.get("push_time", ""), x.get("digest", "")))
            yield artifacts
            if len(artifacts) < 100:
                break
            page += 1