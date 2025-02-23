# InboxFlow IMAP Sync Service

## Overview
This service connects to the IMAP server, fetches unread emails, and stores them in PostgreSQL.

## Setup

### 1. Build the Docker Image
```bash
docker build -t inboxflow-imap-sync .
```

### 2. Run the IMAP Sync Service
```bash
docker run --rm --name inboxflow-imap-sync --network inboxflow-network --env-file .env inboxflow-imap-sync
```

### 3. Check Logs
```bash
docker logs inboxflow-imap-sync --follow
```
