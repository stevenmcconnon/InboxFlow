# InboxFlow Database Schema Updates

## Overview
This migration script updates the database schema to support email flows, filtering, and tracking email syncs.

## Running the Migration

### 1. Ensure PostgreSQL is Running
```bash
docker ps | grep postgres
```

### 2. Run the Migration
```bash
docker exec -it inboxflow-postgres psql -U user -d inboxflow -f migration.sql
```

### 3. Verify the Changes
```bash
docker exec -it inboxflow-postgres psql -U user -d inboxflow -c "\dt"
```
