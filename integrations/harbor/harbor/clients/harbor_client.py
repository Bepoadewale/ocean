from typing import Any, Dict, List, Optional
import base64
import re
from datetime import datetime
from loguru import logger
from port_ocean.utils import http_async_client


class HarborClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.http_client = http_async_client

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
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v2.0/{endpoint.lstrip('/')}"
        
        response = await self.http_client.get(
            url, 
            headers=self.headers, 
            params=params or {}
        )
        
        response.raise_for_status()
        return response.json()

    async def get_projects(
        self, page: int = 1, page_size: int = 100, **filters
    ) -> List[Dict[str, Any]]:
        params = {"page": page, "page_size": page_size}
        
        if "visibility" in filters:
            params["public"] = filters["visibility"] == "public"
        if "owner" in filters:
            params["owner"] = filters["owner"]
            
        projects = await self._make_request("projects", params)
        
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
        
        if filters.get("with_scan_results") or filters.get("min_severity"):
            params["with_scan_overview"] = True
            
        repo_encoded = repository_name.replace("/", "%2F")
        artifacts = await self._make_request(
            f"projects/{project_name}/repositories/{repo_encoded}/artifacts", params
        )
        
        filtered = []
        for artifact in artifacts:
            if filters.get("created_since"):
                try:
                    created = datetime.fromisoformat(artifact.get("push_time", "").replace("Z", "+00:00"))
                    since = datetime.fromisoformat(filters["created_since"])
                    if created < since:
                        continue
                except (ValueError, TypeError):
                    continue
                    
            if filters.get("media_type") and artifact.get("media_type") != filters["media_type"]:
                continue
                    
            if filters.get("max_size_mb"):
                max_bytes = filters["max_size_mb"] * 1024 * 1024
                if artifact.get("size", 0) > max_bytes:
                    continue
                    
            if filters.get("tag_pattern"):
                tags = [tag.get("name", "") for tag in artifact.get("tags", [])]
                pattern = re.compile(filters["tag_pattern"])
                if not any(pattern.match(tag) for tag in tags):
                    continue
                    
            if filters.get("with_scan_results"):
                if not artifact.get("scan_overview", {}):
                    continue
                    
            if filters.get("min_severity"):
                scan_overview = artifact.get("scan_overview", {})
                severity_levels = {"negligible": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
                min_level = severity_levels.get(filters["min_severity"], 0)
                
                has_severity = False
                for scan_result in scan_overview.values():
                    summary = scan_result.get("summary", {})
                    for severity, count in summary.items():
                        if severity_levels.get(severity.lower(), 0) >= min_level and count > 0:
                            has_severity = True
                            break
                    if has_severity:
                        break
                        
                if not has_severity:
                    continue
                    
            filtered.append(artifact)
            
        return filtered