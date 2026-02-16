# Docker Setup Guide

This guide explains how to run the FastAPI issue tracker application with Celery workers using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- No need to have PostgreSQL, Redis, or Python installed locally

## Quick Start

### 1. Clone/Navigate to Project

```bash
cd /path/to/fastapi-issue-tracker
```

### 2. Copy Environment File

```bash
cp .env.example .env
```

The `.env` file contains:
- Database credentials (default: `postgres:postgres`)
- Celery broker and result backend URLs
- Optional: Slack webhook for notifications

### 3. Build and Start Containers

```bash
docker-compose up -d
```

This starts:
- ✅ **FastAPI** (`http://localhost:8000`)
- ✅ **Celery Worker 1** (processes enrichment tasks)
- ✅ **Celery Worker 2** (processes enrichment tasks, optional load balancing)
- ✅ **Celery Flower** monitoring UI (`http://localhost:5555`)
- ✅ **Redis** at `localhost:6379`
- ✅ **PostgreSQL** at `localhost:5432`

### 4. Verify Services are Running

```bash
docker-compose ps
```

Expected output:
```
NAME                 STATUS              PORTS
fastapi-app          Up (healthy)        0.0.0.0:8000->8000/tcp
celery-worker-1      Up (healthy)
celery-worker-2      Up (healthy)
celery-flower        Up (healthy)        0.0.0.0:5555->5555/tcp
redis                Up (healthy)        0.0.0.0:6379->6379/tcp
postgres-db          Up (healthy)        0.0.0.0:5432->5432/tcp
```

## Testing the Setup

### 1. Create an Issue via API

```bash
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Issue from Docker",
    "description": "Testing Celery enrichment in Docker containers",
    "priority": "high"
  }'
```

Expected response:
```json
{
  "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "title": "Test Issue from Docker",
  "description": "Testing Celery enrichment in Docker containers",
  "priority": "high",
  "status": "open",
  "ai_summary": null,
  "tags": null
}
```

### 2. Watch Celery Worker Logs

```bash
docker-compose logs -f celery-worker-1
```

You should see:
```
celery-worker-1  | [2025-02-16 15:45:30,123: INFO/MainProcess] Connected to redis://redis:6379/0
celery-worker-1  | [2025-02-16 15:45:45,456: INFO/ForkPoolWorker-1] Task app.tasks.issues.enrich_issue[abc123def456] received
celery-worker-1  | [2025-02-16 15:45:45,789: INFO/ForkPoolWorker-1] Task app.tasks.issues.enrich_issue[abc123def456] started
celery-worker-1  | [2025-02-16 15:45:50,234: INFO/ForkPoolWorker-1] Task app.tasks.issues.enrich_issue[abc123def456] succeeded in 5.234s: None
```

### 3. Monitor Tasks with Flower

Open `http://localhost:5555` in your browser to see:
- **Live tasks** being executed
- **Worker status** and resource usage
- **Task history** and failures
- **Task details** (duration, arguments, results)

### 4. Verify Database Updates

After ~5 seconds (enrichment time), the issue should be updated with `ai_summary` and `tags`:

```bash
# Connect to PostgreSQL in the container
docker-compose exec db psql -U postgres -d IssueTracker -c "SELECT id, title, ai_summary, tags FROM issue WHERE ai_summary IS NOT NULL LIMIT 1;"
```

Expected output:
```
                  id                  |        title         |                            ai_summary                             |            tags
--------------------------------------+----------------------+------------------------------------------------------------------+---------------------------
 xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | Test Issue from Dock | AI Summary: Testing Celery enrichment in Docker containers       | backend,urgent
```

## Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f celery-worker-1
docker-compose logs -f fastapi
docker-compose logs -f redis
docker-compose logs -f db
```

### Stop Services

```bash
docker-compose stop
```

### Stop and Remove Containers

```bash
docker-compose down
```

### Remove Containers and Volumes (⚠️ Deletes data)

```bash
docker-compose down -v
```

### Rebuild Containers (after code changes)

```bash
docker-compose up -d --build
```

### Run Commands Inside Containers

```bash
# Execute Python command
docker-compose exec fastapi python -c "import app; print('OK')"

# Access bash shell
docker-compose exec fastapi bash

# Postgres CLI
docker-compose exec db psql -U postgres -d IssueTracker

# Redis CLI
docker-compose exec redis redis-cli
```

## Scaling Workers

To handle more concurrent tasks, you can adjust in `docker-compose.yml`:

```yaml
celery-worker-1:
  command: celery -A app.celery_app worker --loglevel=info -n worker1@%h --concurrency=8  # Increased from 4

celery-worker-2:
  command: celery -A app.celery_app worker --loglevel=info -n worker2@%h --concurrency=8  # Increased from 4
```

Then rebuild:
```bash
docker-compose up -d --build
```

Or add more workers by duplicating `celery-worker-2` section.

## Troubleshooting

### "Cannot connect to Redis"
- Check Redis is healthy: `docker-compose ps redis`
- Check logs: `docker-compose logs redis`
- Try: `docker-compose restart redis`

### "Database connection refused"
- Wait a few seconds for PostgreSQL to start
- Check: `docker-compose ps db`
- Verify credentials in `.env` match `docker-compose.yml`

### "Tasks not executing"
- Check workers are running: `docker-compose ps celery-worker-1 celery-worker-2`
- Check worker logs for errors: `docker-compose logs celery-worker-1`
- Verify Redis connection in logs

### Code changes not reflected
- Rebuild containers: `docker-compose up -d --build`
- Or: Restart the service that changed: `docker-compose restart fastapi`

## Production Deployment

For production, consider:

1. **Use managed services instead of containers:**
   - AWS RDS for PostgreSQL
   - AWS ElastiCache for Redis
   - AWS ECS/EKS for application containers

2. **Update environment variables:**
   ```bash
   # Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
   CELERY_BROKER_URL=redis://prod-redis.cache.amazonaws.com:6379/0
   DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.rds.amazonaws.com:5432/db
   ```

3. **Use Docker registries:**
   ```bash
   # Push to ECR, Docker Hub, etc.
   docker build -t myregistry/fastapi-issue-tracker:latest .
   docker push myregistry/fastapi-issue-tracker:latest
   ```

4. **Add health checks and monitoring:**
   - See `docker-compose.yml` for health check examples
   - Integrate with CloudWatch, Datadog, or similar

5. **Scale workers dynamically:**
   - Use Kubernetes HPA (Horizontal Pod Autoscaler)
   - Or: ECS Service with target tracking

See [CELERY_SETUP.md](CELERY_SETUP.md) for more production guidelines.
