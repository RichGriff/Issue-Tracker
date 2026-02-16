FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install uv and sync dependencies
# Note: Remove --frozen to regenerate lock file when dependencies change
RUN pip install uv && uv sync

# Set PATH to include venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY app ./app
COPY main.py .

# Expose port
EXPOSE 8000

# Default command (override in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
