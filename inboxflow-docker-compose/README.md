# InboxFlow Docker Compose for Local PostgreSQL

This `docker-compose.yml` file sets up a local PostgreSQL database for InboxFlow.

## Services

- **postgres**: A PostgreSQL container configured with:
  - **User**: user
  - **Password**: pass
  - **Database**: inboxflow

The container exposes **port 5432** for connectivity and uses a persistent volume `postgres-data`.

## Usage

1. **Start the database**:
   ```bash
   docker-compose up -d
   ```

2. **Stop the database**:
   ```bash
   docker-compose down
   ```

3. **Check logs**:
   ```bash
   docker-compose logs postgres
   ```

4. **Access PostgreSQL CLI**:
   ```bash
   docker exec -it inboxflow-postgres psql -U user -d inboxflow
   ```

5. **Delete all data** (if needed):
   ```bash
   docker volume rm inboxflow-docker-compose_postgres-data
   ```
