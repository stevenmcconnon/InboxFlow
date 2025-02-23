# InboxFlow Setup Guide

## Local Development

### Prerequisites

- Docker & Docker Compose installed
- Python 3.8+ (For backend services)
- Node.js 16+ (For frontend)
- AWS CLI configured (for deployment)

### Steps

1. Clone and set up each service repository.
2. Use Docker Compose to start all services locally.
3. Run tests to verify the setup.

## AWS Deployment

1. Use Terraform to provision infrastructure (`inboxflow-infrastructure` repository).
2. Deploy backend services to ECS/Fargate.
3. Deploy frontend to S3/CloudFront.
4. Configure CI/CD for automatic deployments.
