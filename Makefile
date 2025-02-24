SHELL := /bin/bash

.PHONY: all build-all run-all test-all clean \
        build-dispatcher build-imap-sync build-api build-frontend build-db build-flows \
        run-dispatcher run-imap-sync run-api run-frontend run-db run-flows \
        test-dispatcher test-imap-sync test-api test-frontend test-flows \
        stop-all stop-dispatcher stop-imap-sync stop-api stop-frontend stop-flows \
        deploy-lambda package-lambda local-env prod-env sam-build sam-local \
        deploy-local deploy-prod

# Target to automatically load local environment variables from .env
local-env:
	@echo "Loading local environment from .env..."
	@set -a; source .env; set +a

# Target to automatically load production environment variables from .env.prod
prod-env:
	@echo "Loading production environment from .env.prod..."
	@set -a; source .env.prod; set +a

# Build all services
build-all: build-dispatcher build-imap-sync build-api build-frontend build-flows

build-dispatcher:
	@echo "Building Dispatcher Service..."
	cd inboxflow_dispatcher && docker build -t inboxflow_dispatcher .

build-imap-sync:
	@echo "Building IMAP Sync Service..."
	cd inboxflow-imap-sync && docker build -t inboxflow-imap-sync .

build-api:
	@echo "Building API Service..."
	cd inboxflow-api && docker build -t inboxflow-api .

build-frontend:
	@echo "Building Frontend Service..."
	cd inboxflow-frontend && docker build -t inboxflow-frontend .

build-db:
	@echo "Setting up database migrations..."
	docker cp inboxflow-db/migration.sql inboxflow-postgres:/tmp/migration.sql
	docker exec -it inboxflow-postgres psql -U user -d inboxflow -f /tmp/migration.sqlcf

build-flows:
	@echo "Building Flows Service..."
	cd inboxflow-flows && docker build -t inboxflow-flows .

# Run all services
run-all: run-db run-dispatcher run-api run-frontend run-flows deploy-lambda

run-db:
	@echo "Starting Postgres database container..."
	docker-compose -f inboxflow-docker-compose/docker-compose.yml up -d

run-dispatcher:
	@echo "Running Dispatcher Service..."
	docker stop inboxflow_dispatcher || true
	docker rm inboxflow_dispatcher || true
	docker run -d --name inboxflow_dispatcher --network inboxflow-network \
	  --env-file inboxflow_dispatcher/.env inboxflow_dispatcher

run-imap-sync:
	@echo "Running IMAP Sync Service as container (for local testing)..."
	docker stop inboxflow-imap-sync || true
	docker rm inboxflow-imap-sync || true
	docker run -d --name inboxflow-imap-sync --network inboxflow-network \
	  --env-file inboxflow-imap-sync/.env inboxflow-imap-sync

run-api:
	@echo "Running API Service on port 8000..."
	docker stop inboxflow-api || true
	docker rm inboxflow-api || true
	docker run -d --name inboxflow-api --network inboxflow-network -p 8000:8000 \
	  --env-file inboxflow-api/.env inboxflow-api

run-frontend:
	@echo "Running Frontend Service..."
	docker stop inboxflow-frontend || true
	docker rm inboxflow-frontend || true
	docker run -d --name inboxflow-frontend --network inboxflow-network -p 3000:3000 inboxflow-frontend

run-flows:
	@echo "Running Flows Service..."
	docker stop inboxflow-flows || true
	docker rm inboxflow-flows || true
	docker run -d --name inboxflow-flows --network inboxflow-network inboxflow-flows

# Test all services
test-all: test-dispatcher test-imap-sync test-api test-frontend test-flows

test-dispatcher:
	@echo "Testing Dispatcher Service..."
	cd inboxflow_dispatcher && pytest tests/

test-imap-sync:
	@echo "Testing IMAP Sync Service..."
	cd inboxflow-imap-sync && pytest tests/

test-api:
	@echo "Testing API Service..."
	cd inboxflow-api && pytest tests/

test-frontend:
	@echo "Testing Frontend Service..."
	cd inboxflow-frontend && npm test

test-flows:
	@echo "Testing Flows Service..."
	cd inboxflow-flows && pytest tests/

# Stop all services
stop-all:
	@echo "Stopping all running services..."
	docker stop inboxflow_dispatcher inboxflow-imap-sync inboxflow-api inboxflow-frontend inboxflow-flows || true

stop-dispatcher:
	@echo "Stopping Dispatcher Service..."
	docker stop inboxflow_dispatcher || true

stop-imap-sync:
	@echo "Stopping IMAP Sync Service..."
	docker stop inboxflow-imap-sync || true

stop-api:
	@echo "Stopping API Service..."
	docker stop inboxflow-api || true

stop-frontend:
	@echo "Stopping Frontend Service..."
	docker stop inboxflow-frontend || true

stop-flows:
	@echo "Stopping Flows Service..."
	docker stop inboxflow-flows || true

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	docker system prune -f

# Package the Lambda function into a zip file
package-lambda:
	@echo "Packaging Lambda function..."
	./package_lambda.sh

# Deploy Lambda using Terraform for local environment (uses .env)
deploy-lambda: local-env package-lambda
	@echo "Deploying Lambda function and infrastructure via Terraform (local)..."
	cd inboxflow-infrastructure && terraform init && terraform apply -auto-approve

# SAM CLI Targets for Local Development
sam-build:
	@echo "Building Lambda with SAM CLI..."
	sam build

sam-local:
	@echo "Starting SAM local API..."
	sam local start-api

# Deploy local and production via Terraform workspaces
deploy-local:
	@echo "Deploying to local (using local-dev workspace)..."
	cd inboxflow-infrastructure && \
	terraform workspace select local-dev || terraform workspace new local-dev && \
	terraform apply -var="local_dev=true" -auto-approve

deploy-prod:
	@echo "Deploying to AWS production (using default workspace)..."
	cd inboxflow-infrastructure && \
	terraform workspace select default || terraform workspace new default && \
	terraform apply -var="local_dev=false" -var-file="terraform.prod.tfvars" -auto-approve