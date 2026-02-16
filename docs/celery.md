# Plan: Implement Celery + Redis Background Tasks

**TL;DR:** Install Celery with Redis broker, convert `enrich_issue` to a Celery task, update the API endpoint to queue the task instead of using `BackgroundTasks`, and run a worker process. This gives you reliable task queuing, retries, and visibility into failed enrichments—with minimal changes to your existing code.

**Key decision:** Recommending **Celery** (industry standard, production-ready) over RQ. Celery excels with multiple distributed workers and integrates seamlessly with FastAPI.

---

## Steps

### **1. Install Celery and Redis Client**
   - Add `celery[redis]>=5.3.0` to [pyproject.toml](pyproject.toml)
   - This installs Celery and the `redis` Python client
   - No need to install Redis server itself (you have it available)

### **2. Create Celery Configuration Module** — new file `app/celery_app.py`
   - Import and configure Celery with Redis as broker
   - Set broker URL (e.g., `redis://localhost:6379/0`)
   - Configure task settings: serializer, timezone, result backend (optional)
   - Enable task auto-discovery so Celery finds `@app.task` decorated functions
   - **Why:** Centralizes Celery config and makes it reusable across the app

### **3. Convert `enrich_issue` to a Celery Task** — modify [app/tasks/issues.py](app/tasks/issues.py)
   - Import the Celery app from `app/celery_app`
   - Decorate `enrich_issue` with `@app.task(bind=True, max_retries=3)`
   - Replace `AsyncSessionLocal()` with a synchronous database session (Celery tasks are sync by default)
   - Replace blocking `time.sleep(5)` with `celery.current_app.send_task()` or direct async-to-sync adapter
   - Add retry logic: `self.retry(exc=error, countdown=60)` for transient failures
   - Remove the async/await syntax since Celery tasks are synchronous by default
   - **Why:** Celery tasks must be synchronous and serializable; they run in separate processes

### **4. Update API Endpoint** — modify [app/routes/issues.py](app/routes/issues.py)
   - Remove `background_tasks: BackgroundTasks` parameter from `create_issue` endpoint
   - Replace `background_tasks.add_task(enrich_issue, issue_id=...)` with `enrich_issue.delay(issue_id=...)`
   - This queues the task to Redis instead of running it in-process
   - Optionally get the task ID: `task = enrich_issue.delay(issue_id=...); task.id`
   - **Why:** `.delay()` is how Celery tasks are invoked; they're queued immediately and return a task ID

### **5. Create Task Broker Connection** — update [main.py](main.py) if needed
   - Optional: Add Celery app initialization to lifespan for graceful shutdown
   - Celery typically runs independently, but this ensures cleanup
   - **Why:** Ensures Celery connection pooling is properly managed

### **6. Create Celery Worker Start Script** — new file or update docs
   - Document how to start the worker: `celery -A app.celery_app worker --loglevel=info`
   - Worker processes consume tasks from Redis queue and execute them
   - Can run single or multiple workers for concurrency
   - **Why:** Worker processes are the actual executors—without them, tasks just queue

### **7. Database Session Management** — handle sync/async mismatch
   - Celery is synchronous; your DB uses `AsyncSessionLocal` (async)
   - Create a synchronous session factory or use `asyncio.run()` adapter
   - OR: Keep async DB and wrap task code with `asyncio.run(async_func())`
   - **Why:** Celery worker processes can't directly use async SQLAlchemy sessions

### **8. Monitoring & Debugging** — optional but recommended
   - Use Celery Flower (`pip install flower`): web UI to monitor tasks
   - Start: `celery -A app.celery_app events` (for Flower to collect events)
   - Flower: `celery -A app.celery_app flower` → visit `http://localhost:5555`
   - Log task execution and failures in task code
   - **Why:** Visibility into task queue, failed tasks, and worker health

---

## Verification

1. **Test locally:**
   - Start your FastAPI app: `python -m uvicorn main:app --reload`
   - Start a Celery worker: `celery -A app.celery_app worker --loglevel=info`
   - Create an issue via API endpoint (POST `/issues`)
   - Verify worker logs show task execution
   - Check database records: `ai_summary` and `tags` should be populated after ~5 seconds

2. **Validate retry logic:**
   - Simulate task failure by intentionally breaking DB query
   - Worker should retry up to 3 times (with delays between attempts)
   - After max retries, task moves to failed state (visible in logs or Flower)

3. **Check task queuing:**
   - Stop the worker
   - Create multiple issues
   - Redis command: `redis-cli LLEN celery` to see queued tasks
   - Start worker again—it should process all queued tasks

---

## Decisions

- **Celery vs. RQ:** Chose Celery because you explicitly mentioned it and it's industry-standard for mature async task handling with better scaling and monitoring options.
- **Sync tasks:** Celery tasks are synchronous. Your `enrich_issue` needs refactoring from async to sync or require an `asyncio.run()` bridge.
- **Database sessions:** Will use **synchronous SQLAlchemy sessions** created fresh per task (simpler than async-to-sync adapters).
- **Redis broker:** Assumes Redis is available at `localhost:6379`. Configuration is parameterizable for different environments.
- **Scope:** Only `enrich_issue` per your request; `notify_issue_creation` remains with `BackgroundTasks` for now.
- **Retries:** Simple max 3 retries with increasing backoff (Celery's default: 60s, 120s, 240s).