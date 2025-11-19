# Harbor Integration for Port Ocean

This integration syncs Harbor container registry data into Port, enabling platform and security teams to visualize images, projects, users, and relationships across their software supply chain.

## Features

- **Full Sync**: Sync all Harbor projects, users, repositories, and artifacts
- **Real-time Updates**: Webhook support for artifact push, scan completion, and deletion events
- **Advanced Filtering**: Comprehensive filtering options for all resource types
- **Security Focus**: Vulnerability scan integration with severity-based filtering
- **Performance**: Async operations with pagination and parallel processing

## Configuration

### Required Configuration

```yaml
harborUrl: "https://harbor.example.com"  # Your Harbor instance URL
harborUsername: "admin"                  # Harbor username (admin or robot account)
harborPassword: "your-password"          # Harbor password or robot token
```

### Optional Configuration

```yaml
webhookSecret: "your-secret"        # Secret for webhook signature validation
```

## Filtering Options

### Projects
- `visibility`: Filter by "public" or "private"
- `namePrefix`: Filter by name prefix
- `nameRegex`: Filter by regex pattern
- `owner`: Filter by owner

### Users
- `adminOnly`: Only sync admin users
- `emailDomain`: Filter by email domain

### Repositories
- `projectName`: Filter by specific project
- `nameContains`: Filter by name pattern
- `nameStartsWith`: Filter by name prefix
- `minArtifactCount`: Minimum artifact count
- `minPullCount`: Minimum pull count

### Artifacts
- `projectName`: Filter by project
- `repositoryName`: Filter by repository
- `tagPattern`: Filter by tag regex
- `createdSince`: Filter by creation date (ISO format)
- `mediaType`: Filter by media type
- `withScanResults`: Only artifacts with vulnerability scans
- `minSeverity`: Minimum vulnerability severity (negligible, low, medium, high, critical)
- `maxSizeMb`: Maximum artifact size in MB

## Webhooks

The integration supports Harbor webhook events:

- **Artifact Events**: Push, delete, scan completion
- **Repository Events**: Delete
- **Project Events**: Delete

Configure webhooks in Harbor to point to:
- `/webhooks/harbor` (single endpoint for all events)
- `/webhooks/artifacts` (artifact-specific events)
- `/webhooks/repositories` (repository-specific events)
- `/webhooks/projects` (project-specific events)

**Note**: Webhooks require the integration to be running with a publicly accessible URL.

## Port Entities

### Harbor Project
- **Identifier**: Project name
- **Properties**: Name, visibility, description, creation/update time, repository count, storage usage
- **Relations**: None

### Harbor User
- **Identifier**: Username
- **Properties**: Username, email, real name, admin flag, creation/update time
- **Relations**: None

### Harbor Repository
- **Identifier**: Repository name (with "/" replaced by "_")
- **Properties**: Name, description, artifact count, pull count, creation/update time
- **Relations**: Project

### Harbor Artifact
- **Identifier**: Digest
- **Properties**: Digest, media type, size, push/pull time, tags, vulnerability scan results
- **Relations**: Repository, Project

## Prerequisites

- **Port Ocean Framework**: Must have Port Ocean installed
- **Harbor Instance**: Running Harbor registry (v2.0+)
- **Port Account**: Valid Port credentials for data syncing

## Setup

1. Copy `.env.example` to `.env` and configure your Harbor credentials:

```bash
cp .env.example .env
# Edit .env with your Harbor URL, username, and password
```

2. Run the integration (requires Ocean framework):

```bash
ocean sail .
```

## Development

**Note**: Development commands require the Ocean framework environment.

### Testing
```bash
make test
```

### Linting
```bash
make lint
```