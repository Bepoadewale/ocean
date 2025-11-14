import pytest
from unittest.mock import AsyncMock, MagicMock
from harbor.clients.harbor_client import HarborClient
from harbor.core.exporters import ProjectExporter, UserExporter
from harbor.webhook_processors.artifact_processor import ArtifactWebhookProcessor


class TestHarborClient:
    @pytest.fixture
    def mock_http_client(self):
        client = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = []
        response.raise_for_status.return_value = None
        client.get.return_value = response
        return client

    @pytest.fixture
    def harbor_client(self, mock_http_client):
        client = HarborClient(
            base_url="https://harbor.test.com",
            username="admin",
            password="password"
        )
        client.http_client = mock_http_client
        return client

    @pytest.mark.asyncio
    async def test_get_projects(self, harbor_client, mock_http_client):
        mock_http_client.get.return_value.json.return_value = [
            {"name": "test-project", "metadata": {"public": "false"}}
        ]
        
        projects = await harbor_client.get_projects()
        assert len(projects) == 1
        assert projects[0]["name"] == "test-project"

    @pytest.mark.asyncio
    async def test_get_projects_with_filters(self, harbor_client, mock_http_client):
        mock_http_client.get.return_value.json.return_value = [
            {"name": "test-project", "metadata": {"public": "false"}},
            {"name": "other-project", "metadata": {"public": "true"}}
        ]
        
        projects = await harbor_client.get_projects(name_prefix="test")
        assert len(projects) == 1
        assert projects[0]["name"] == "test-project"


class TestExporters:
    @pytest.fixture
    def mock_client(self):
        client = AsyncMock()
        client.get_paginated_projects.return_value.__aiter__ = AsyncMock(return_value=iter([
            [{"name": "project1"}, {"name": "project2"}]
        ]))
        return client

    @pytest.mark.asyncio
    async def test_project_exporter(self, mock_client):
        exporter = ProjectExporter(mock_client)
        
        results = []
        async for batch in exporter.get_paginated_resources():
            results.extend(batch)
            
        assert len(results) == 2
        assert results[0]["name"] == "project1"

    @pytest.mark.asyncio
    async def test_user_exporter(self, mock_client):
        mock_client.get_paginated_users.return_value.__aiter__ = AsyncMock(return_value=iter([
            [{"username": "admin"}, {"username": "user1"}]
        ]))
        
        exporter = UserExporter(mock_client)
        
        results = []
        async for batch in exporter.get_paginated_resources():
            results.extend(batch)
            
        assert len(results) == 2
        assert results[0]["username"] == "admin"


class TestWebhookProcessors:
    @pytest.fixture
    def mock_client(self):
        client = AsyncMock()
        client.get_artifacts.return_value = [
            {"digest": "sha256:abc123", "tags": [{"name": "latest"}]}
        ]
        return client

    @pytest.fixture
    def artifact_processor(self, mock_client):
        processor = ArtifactWebhookProcessor()
        processor.client = mock_client
        return processor

    @pytest.mark.asyncio
    async def test_artifact_push_event(self, artifact_processor):
        event_data = {"type": "PUSH_ARTIFACT"}
        resource_info = {
            "event_type": "PUSH_ARTIFACT",
            "project_name": "test-project",
            "repository_name": "test-repo",
            "artifact_digest": "sha256:abc123"
        }
        
        result = await artifact_processor._process_event(event_data, resource_info)
        assert len(result) == 1
        assert result[0]["digest"] == "sha256:abc123"
        assert result[0]["project_name"] == "test-project"

    @pytest.mark.asyncio
    async def test_artifact_delete_event(self, artifact_processor):
        event_data = {"type": "DELETE_ARTIFACT"}
        resource_info = {
            "event_type": "DELETE_ARTIFACT",
            "project_name": "test-project",
            "repository_name": "test-repo",
            "artifact_digest": "sha256:abc123"
        }
        
        result = await artifact_processor._process_event(event_data, resource_info)
        assert len(result) == 0  # Delete events return empty list