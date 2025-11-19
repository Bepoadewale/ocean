# Changelog - Ocean - Harbor

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- towncrier release notes start -->

## 1.0.0 (2024-11-18)

### Features

- Initial Harbor integration implementation
- Support for syncing Harbor projects with visibility and metadata filtering
- Support for syncing Harbor users with admin and email domain filtering  
- Support for syncing Harbor repositories with project and name-based filtering
- Support for syncing Harbor artifacts with comprehensive filtering (tags, size, vulnerability scans)
- Real-time webhook support for artifact push, scan completion, and deletion events
- Async HTTP client with built-in retry and pagination support
- Configurable filtering options for all resource types
- Webhook signature validation for secure event processing
- Vulnerability scan integration with severity-based filtering
- Parallel processing with semaphores for improved performance
- Comprehensive logging for API requests, webhooks, and ingestion statistics