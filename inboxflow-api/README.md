# InboxFlow API Service

## Overview
This API serves as the backend for InboxFlow, exposing endpoints for email management, approvals, and IMAP sync.

## Setup

### 1. Build the Docker Image
```bash
docker build -t inboxflow-api .
```

### 2. Run the API Service
```bash
docker run --rm --name inboxflow-api --network inboxflow-network -p 8000:8000 --env-file .env inboxflow-api
```

### 3. Check If API is Running
```bash
curl -X GET http://localhost:8000/emails
```
