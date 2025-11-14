# Harbor Integration

This integration syncs Harbor registry data with Port, providing visibility into your container registry infrastructure.

## Features

- **Projects**: Sync Harbor projects with visibility, storage usage, and repository counts
- **Users**: Import Harbor users with admin flags and creation details  
- **Repositories**: Track repositories with artifact counts and pull statistics
- **Artifacts**: Monitor container images with vulnerability scan results and tags
- **Real-time Updates**: Webhook support for push, delete, and scan events
- **Advanced Filtering**: Comprehensive filtering options for all entity types
- **Parallel Processing**: Efficient data ingestion with rate limiting

## Configuration

### Required Settings

- `harborUrl`: Harbor instance URL (e.g., https://harbor.example.com)
- `harborUsername`: Harbor username (admin or robot account)
- `harborPassword`: Harbor password or robot token

### Optional Settings

- `maxConcurrentRequests`: Maximum concurrent API requests (default: 10)
- `requestTimeout`: Request timeout in seconds (default: 30)
- `rateLimitDelay`: Delay between requests in seconds (default: 1)
- `verifySsl`: Verify SSL certificates (default: true)
- `webhookSecret`: Secret for webhook signature validation

## Filtering Options

### Projects
- `visibility`: Filter by public/private
- `namePrefix`: Filter by name prefix
- `nameRegex`: Filter by name regex pattern
- `owner`: Filter by project owner

### Users
- `adminOnly`: Only sync admin users
- `emailDomain`: Filter by email domain

### Repositories
- `projectName`: Filter by project name
- `nameContains`: Filter by name pattern
- `nameStartsWith`: Filter by name prefix
- `minArtifactCount`: Minimum artifact count
- `minPullCount`: Minimum pull count

### Artifacts
- `projectName`: Filter by project name
- `repositoryName`: Filter by repository name
- `tagPattern`: Filter by tag pattern
- `createdSince`: Filter by creation date
- `mediaType`: Filter by media type
- `withScanResults`: Only include scanned artifacts
- `minSeverity`: Minimum vulnerability severity
- `maxSizeMb`: Maximum artifact size in MB

## Webhooks

The integration supports Harbor webhooks for real-time updates:

- **Artifact Events**: Push and delete notifications
- **Repository Events**: Repository deletion notifications  
- **Project Events**: Project lifecycle notifications

Configure webhooks in Harbor to point to:
- `/webhooks/harbor` (unified endpoint)
- `/webhooks/artifacts` (artifact-specific)
- `/webhooks/repositories` (repository-specific)
- `/webhooks/projects` (project-specific)

## Entity Relationships

- **Projects** contain **Repositories**
- **Repositories** contain **Artifacts**
- **Artifacts** belong to both **Projects** and **Repositories**

## Security

- Uses Harbor's basic authentication
- Supports robot accounts for enhanced security
- Optional webhook signature validation
- SSL certificate verification (configurable)