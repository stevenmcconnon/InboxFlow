# InboxFlow

InboxFlow is a modular, event-driven communication automation platform. This repository contains multiple services including a Lambda-based IMAP sync module, an API, a frontend, and more.

## Table of Contents
- [Project Structure](#project-structure)
- [Automated Local Environment Setup](#automated-local-environment-setup)
- [Building, Packaging, and Deployment](#building-packaging-and-deployment)
- [Running and Testing Services](#running-and-testing-services)
- [Unified Environment Startup](#unified-environment-startup)
- [Production Deployment](#production-deployment)
- [Additional Notes](#additional-notes)

---

## Project Structure

- **inboxflow_dispatcher/**: Contains the Dispatcher Service.
- **inboxflow_imap-sync/**: Contains the IMAP sync service.
- **inboxflow_api/**: Contains the API service.
- **inboxflow_frontend/**: Contains the frontend UI.
- **inboxflow_infrastructure/**: Contains Terraform configurations for infrastructure.
- **inboxflow_docker-compose/**: Contains Docker Compose configuration (e.g., for the Postgres database).
- **Makefile**: Contains targets for building, running, testing services, packaging the Lambda function, and deploying via Terraform.

---

## Automated Local Environment Setup

1. **Environment Configuration**  
   Ensure you have a `.env` file in the project root with your local environment variables.

2. **Starting LocalStack**  
   Run:  
   ```make localstack-up```  
   This command starts LocalStack with the Docker socket mounted so that Lambda functions can run using Docker.

3. **Starting the Database**  
   Instead of manually switching to the docker-compose directory, use:  
   ```make run-db```  
   This target uses Docker Compose (with the configuration in the ```inboxflow_docker-compose``` folder) to start the Postgres container and mount the migration file for automatic initialization.  
   **Note:** The migration file is automatically applied only when the database is created (i.e., when the data volume is empty).

---

## Building, Packaging, and Deployment

- **Packaging the Lambda Function**  
  Run:  
  ```make package-lambda```  
  This packages your IMAP sync Lambda function.

- **Deploying with Terraform**  
  Run:  
  ```make deploy-lambda```  
  This deploys your Lambda and associated infrastructure (using LocalStack endpoints).

- **Building All Services**  
  Run:  
  ```make build-all```  
  This builds Docker images for all services (including database migration if applicable).

---

## Running and Testing Services

- **Running All Services**  
  Run:  
  ```make run-all```  
  This target now includes starting the database (via ```run-db```), the dispatcher, API, frontend, and flows services.

- **Running Tests**  
  Run:  
  ```make test-all```  
  This executes test suites for all services.

---

## Unified Environment Startup

To streamline your workflow and reduce the number of steps, you can now start the entire local environment with just one command. The new setup ensures that LocalStack, the Postgres database (with automatic migration), and all services are started together. Simply run:

```make run-all```

This command will:
- Start the Postgres database container using Docker Compose (via the ```run-db``` target).
- Build and start all services (dispatcher, API, frontend, flows, etc.).
- Ensure that the migration file is mounted and applied automatically on first run.

---

## Production Deployment

For production deployment:
- Create a production environment file (e.g., ```.env.prod```) with real AWS credentials and settings.
- Update Terraform variable files as needed.
- Run:  
  ```make deploy-prod```

---

## Additional Notes

- **Environment Switching:**  
  Use ```make local-env``` for local settings and ```make prod-env``` (if configured) for production settings.

- **Automation:**  
  The Makefile automates environment setup, migration, building, and running services. This can be integrated into your CI/CD pipeline.

- **Resource Exposure:**  
  The frontend is publicly exposed while backend resources remain secured.