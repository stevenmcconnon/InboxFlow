# InboxFlow Dispatcher Service

## Overview
This service processes emails that have been stored in PostgreSQL and categorizes them based on user-defined flows.

## Setup

### 1. Build the Docker Image
```bash
docker build -t inboxflow_dispatcher .
```

### 2. Run the Dispatcher Service
```bash
docker run --rm --name inboxflow_dispatcher --network inboxflow-network --env-file .env inboxflow_dispatcher
```

### 3. Check Logs
```bash
docker logs inboxflow_dispatcher --follow
```
