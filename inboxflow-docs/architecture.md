# InboxFlow Architecture

## Overview

InboxFlow is designed as a modular, event-driven communication automation system leveraging AWS serverless and autoscaling technologies.

### Core Components

1. **Dispatcher Service** (Polls inbox, enqueues tasks to SQS)
2. **Worker Service** (Processes tasks, applies AI/NLP, generates responses)
3. **API Service** (Exposes RESTful endpoints for interaction)
4. **Frontend Service** (React-based UI for users)
5. **Infrastructure** (Terraform-managed AWS setup: ECS, Lambda, API Gateway, Aurora Serverless)
6. **CI/CD Pipelines** (Automated builds and deployments)
