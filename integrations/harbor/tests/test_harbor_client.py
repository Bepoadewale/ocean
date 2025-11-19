import pytest
from unittest.mock import AsyncMock, patch
from harbor.clients.harbor_client import HarborClient


@pytest.fixture
def harbor_client():
    return HarborClient(
        base_url="https://harbor.example.com",
        username="test-user",
        password="test-password"
    )


@pytest.mark.asyncio
async def test_get_projects(harbor_client):
    """Test getting projects from Harbor."""
    mock_response = [
        {
            "name": "library",
            "project_id": 1,
            "creation_time": "2023-01-01T00:00:00Z",
            "metadata": {"public": "true"}
        }
    ]
    
    with patch.object(harbor_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        projects = await harbor_client.get_projects()
        
        assert len(projects) == 1
        assert projects[0]["name"] == "library"
        mock_request.assert_called_once_with("projects", {"page": 1, "page_size": 100})


@pytest.mark.asyncio
async def test_get_projects_with_filters(harbor_client):
    """Test getting projects with filters."""
    mock_response = [
        {
            "name": "public-project",
            "project_id": 1,
            "creation_time": "2023-01-01T00:00:00Z",
            "metadata": {"public": "true"}
        }
    ]
    
    with patch.object(harbor_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        projects = await harbor_client.get_projects(visibility="public", name_prefix="public")
        
        assert len(projects) == 1
        assert projects[0]["name"] == "public-project"
        
        expected_params = {
            "page": 1,
            "page_size": 100,
            "public": True
        }
        mock_request.assert_called_once_with("projects", expected_params)


@pytest.mark.asyncio
async def test_get_repositories(harbor_client):
    """Test getting repositories from Harbor."""
    mock_response = [
        {
            "name": "library/nginx",
            "artifact_count": 1,
            "pull_count": 0,
            "creation_time": "2023-01-01T00:00:00Z"
        }
    ]
    
    with patch.object(harbor_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        repos = await harbor_client.get_repositories("library")
        
        assert len(repos) == 1
        assert repos[0]["name"] == "library/nginx"
        mock_request.assert_called_once_with("projects/library/repositories", {"page": 1, "page_size": 100})


@pytest.mark.asyncio
async def test_get_artifacts(harbor_client):
    """Test getting artifacts from Harbor."""
    mock_response = [
        {
            "digest": "sha256:abc123",
            "media_type": "application/vnd.docker.container.image.v1+json",
            "size": 1000000,
            "push_time": "2023-01-01T00:00:00Z",
            "tags": [{"name": "latest"}]
        }
    ]
    
    with patch.object(harbor_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        artifacts = await harbor_client.get_artifacts("library", "nginx")
        
        assert len(artifacts) == 1
        assert artifacts[0]["digest"] == "sha256:abc123"
        mock_request.assert_called_once_with("projects/library/repositories/nginx/artifacts", {"page": 1, "page_size": 100})