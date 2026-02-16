# Celery Worker Setup & Running Guide

This document explains how to set up and run the Celery worker process for handling background tasks (like issue enrichment).

## Prerequisites

1. **Redis Server Running**: Celery uses Redis as the message broker
   - Verify Redis is running: `redis-cli ping` (should return `PONG`)
   - Default location: `localhost:6379`

2. **Dependencies Installed**: Run `pip install -r requirements.txt` or similar
   - Celery is now in `pyproject.toml` and installed automatically

## Running the Celery Worker

### Basic Worker (Single Process)

```bash
celery -A app.celery_app worker --loglevel=info
```

**What this does:**
- Starts a Celery worker that connects to Redis at `localhost:6379/0`
- Continuously listens for tasks queued by the FastAPI application
- Logs at "info" level (shows task execution, retries, failures)
- Pulls tasks from the `default` and `issues` queues

### Worker Output Example

```
celery@your-machine v5.3.0 (emerald-rush)

[config]
.> app:         app.celery_app:0x...
.> transport:   redis://localhost:6379/0
.> results:     redis://localhost:6379/1
.> concurrency: 4 (prefork)
.> task events: ON

[queues]
.> issues             exchange=issues(direct) key=issues
.> default            exchange=default(direct) key=default

[tasks]
  . app.tasks.issues.enrich_issue

[2025-02-16 10:30:45,123: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-02-16 10:30:45,345: INFO/MainProcess] mingle: searching for executable...
[2025-02-16 10:30:45,456: INFO/MainProcess] celery@your-machine ready.

[2025-02-16 10:31:22,123: INFO/ForkPoolWorker-1] Task app.tasks.issues.enrich_issue[abc123def456] received
[2025-02-16 10:31:22,456: INFO/ForkPoolWorker-1] Task app.tasks.issues.enrich_issue[abc123def456] started
[2025-02-16 10:31:27,890: INFO/ForkPoolWorker-1] Task app.tasks.issues.enrich_issue[abc123def456] succeeded in 5.234s: None
```

## Testing the Setup

### 1. Terminal 1: Start FastAPI Application

```bash
python -m uvicorn main:app --reload
```

Your API will be available at `http://localhost:8000`

### 2. Terminal 2: Start Celery Worker

```bash
celery -A app.celery_app worker --loglevel=info
```

Watch for the "ready" message and task logs.

### 3. Terminal 3: Create a Test Issue

```bash
curl -X POST http://localhost:8000/api/v1/issues \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Issue",
    "description": "This is a test issue for Celery enrichment",
    "priority": "high"
  }'
```

**Expected behavior:**
- FastAPI immediately returns the issue (without waiting for enrichment)
- Worker terminal shows:
  - Task received
  - Task started
  - After ~5 seconds: Task succeeded
- Database is updated with `ai_summary` and `tags` fields

### 4. Verify Database Updates

```bash
# Connect to PostgreSQL
psql -U postgres -d IssueTracker

# SQL to verify enrichment
SELECT id, title, ai_summary, tags FROM issue WHERE ai_summary IS NOT NULL LIMIT 1;
```

Expected output:
```
                  id                  |   title    |              ai_summary              |           tags
--------------------------------------+------------+--------------------------------------+---------------------------
 xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | Test Issue | AI Summary: This is a test issue f... | bug,frontend
```

## Advanced: Multiple Workers

Run multiple worker processes to handle concurrent tasks:

```bash
# Worker 1
celery -A app.celery_app worker --loglevel=info --concurrency=4 -n worker1@%h

# Worker 2 (in another terminal)
celery -A app.celery_app worker --loglevel=info --concurrency=4 -n worker2@%h
```

This creates 2 workers, each with 4 concurrent processes (8 total concurrent tasks).

## Monitoring: Celery Flower

Flower is a real-time monitoring tool with a web UI.

### Install Flower

```bash
pip install flower
```

### Run Flower

```bash
celery -A app.celery_app flower --port=5555
```

Visit `http://localhost:5555` to see:
- **Tasks**: Live task execution, completion, failures
- **Workers**: Worker status and statistics
- **Pools**: Worker process details
- **Tasks History**: Completed and failed tasks

## Configuration Reference

See `app/celery_app.py` for current settings:

| Setting | Value | Explanation |
|---------|-------|-------------|
| Transport | Redis | Message broker for task queues |
| Broker URL | `redis://localhost:6379/0` | Where tasks are queued |
| Result Backend | `redis://localhost:6379/1` | Where task results are stored |
| Serializer | JSON | Tasks and results serialized as JSON (safe, language-agnostic) |
| Task Acks Late | True | Worker acknowledges task only after execution (safer for retries) |
| Prefetch Multiplier | 1 | Worker fetches 1 task at a time (prevents starvation on long-running tasks) |

## Handling Task Failures & Retries

### Automatic Retries

The `enrich_issue` task is configured with:
- **Max retries**: 3
- **Retry interval**: 60 seconds (first retry), 120 seconds (second), 240 seconds (third)

When a task fails:
1. Worker logs the error
2. Task is re-queued with a delay
3. Worker picks it up and tries again
4. After 3 failed attempts, task moves to "failed" state

### Manual Intervention

You can inspect failed tasks in Flower:
1. Go to `http://localhost:5555` → Tasks
2. Filter by "Failed" state
3. View error details and retry manually

Or use Redis CLI:

```bash
# Check task states in Redis
redis-cli

# View all keys (tasks, results, etc.)
> KEYS *

# Get task status
> GET celery-task-meta-<task_id>
```

## Troubleshooting

### "Cannot connect to redis://localhost:6379/0"
- Ensure Redis is running: `redis-cli ping`
- Check Redis configuration in `app/celery_app.py`
- Verify network connectivity

### "Task not executing / Worker not picking up tasks"
- Check worker is showing "ready" in logs
- Verify task is being queued: `redis-cli LLEN celery` (should show > 0)
- Check worker has a connection to Redis

### "Task stuck or very slow"
- Check database connection in worker terminal
- Monitor via Flower: `http://localhost:5555`
- Check PostgreSQL is responding: `psql -c "SELECT 1"`

### Database connection errors in tasks
- Verify `SyncSessionLocal` in `app/database/config.py` has correct DB credentials
- Test connection: `psql -U postgres -d IssueTracker -c "SELECT 1"`

## Environment Variables

If needed, configure via environment or `.env`:

```bash
# Redis broker
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Database (for sync sessions in Celery)
export DATABASE_URL=postgresql://postgres:password@localhost:5432/IssueTracker
```

## Production Notes

For production deployments:

1. **Use process supervisor** (systemd, supervisor, Docker)
2. **Multiple workers** across multiple machines for high availability
3. **Use a dedicated Redis instance** (don't use localhost)
4. **Monitor with Flower** or similar tools
5. **Set up log aggregation** to track task execution across workers
6. **Use environment-specific configuration** (retries, timeouts, etc.)
7. **Dead-letter queue** for tasks that fail repeatedly

See production guidelines in the main project documentation.
