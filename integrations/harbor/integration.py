from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from port_ocean.core.handlers.port_app_config.models import PortAppConfig, ResourceConfig, Selector
from port_ocean.core.integrations.base import BaseIntegration
from port_ocean.core.handlers.port_app_config.api import APIPortAppConfig


class HarborProjectSelector(Selector):
    visibility: Optional[Literal["public", "private"]] = Field(
        default=None, description="Filter projects by visibility"
    )
    name_prefix: Optional[str] = Field(
        default=None, alias="namePrefix", description="Filter projects by name prefix"
    )
    name_regex: Optional[str] = Field(
        default=None, alias="nameRegex", description="Filter projects by name regex pattern"
    )
    owner: Optional[str] = Field(
        default=None, description="Filter projects by owner"
    )


class HarborUserSelector(Selector):
    admin_only: bool = Field(
        default=False, alias="adminOnly", description="Only sync admin users"
    )
    email_domain: Optional[str] = Field(
        default=None, alias="emailDomain", description="Filter users by email domain"
    )


class HarborRepositorySelector(Selector):
    project_name: Optional[str] = Field(
        default=None, alias="projectName", description="Filter repositories by project name"
    )
    name_contains: Optional[str] = Field(
        default=None, alias="nameContains", description="Filter repositories by name pattern"
    )
    name_starts_with: Optional[str] = Field(
        default=None, alias="nameStartsWith", description="Filter repositories by name prefix"
    )
    min_artifact_count: Optional[int] = Field(
        default=None, alias="minArtifactCount", description="Minimum artifact count"
    )
    min_pull_count: Optional[int] = Field(
        default=None, alias="minPullCount", description="Minimum pull count"
    )


class HarborArtifactSelector(Selector):
    project_name: Optional[str] = Field(
        default=None, alias="projectName", description="Filter artifacts by project name"
    )
    repository_name: Optional[str] = Field(
        default=None, alias="repositoryName", description="Filter artifacts by repository name"
    )
    tag_pattern: Optional[str] = Field(
        default=None, alias="tagPattern", description="Filter artifacts by tag pattern"
    )
    created_since: Optional[str] = Field(
        default=None, alias="createdSince", description="Filter artifacts created since date (ISO format)"
    )
    media_type: Optional[str] = Field(
        default=None, alias="mediaType", description="Filter by media type"
    )
    with_scan_results: bool = Field(
        default=False, alias="withScanResults", description="Only include artifacts with vulnerability scan results"
    )
    min_severity: Optional[Literal["negligible", "low", "medium", "high", "critical"]] = Field(
        default=None, alias="minSeverity", description="Minimum vulnerability severity threshold"
    )
    max_size_mb: Optional[int] = Field(
        default=None, alias="maxSizeMb", description="Maximum artifact size in MB"
    )


class HarborProjectConfig(ResourceConfig):
    kind: Literal["harbor-project"]
    selector: HarborProjectSelector


class HarborUserConfig(ResourceConfig):
    kind: Literal["harbor-user"]
    selector: HarborUserSelector


class HarborRepositoryConfig(ResourceConfig):
    kind: Literal["harbor-repository"]
    selector: HarborRepositorySelector


class HarborArtifactConfig(ResourceConfig):
    kind: Literal["harbor-artifact"]
    selector: HarborArtifactSelector


class HarborPortAppConfig(PortAppConfig):
    resources: List[
        HarborProjectConfig
        | HarborUserConfig
        | HarborRepositoryConfig
        | HarborArtifactConfig
        | ResourceConfig
    ] = Field(default_factory=list)


class HarborIntegration(BaseIntegration):
    class AppConfigHandlerClass(APIPortAppConfig):
        CONFIG_CLASS = HarborPortAppConfig