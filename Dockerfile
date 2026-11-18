# ==============================================================================
# AgentIQ v2 Backend Production Dockerfile
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps

# Install dependencies into virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Runtime Stage
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime dependencies (e.g. curl for health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app:/app/packages:/app/apps"
ENV PYTHONUNBUFFERED=1

# Create non-root application user
RUN groupadd -r agentiq && useradd -r -g agentiq -d /app -s /sbin/nologin agentiq

# Copy application source code
COPY alembic.ini .
COPY migrations migrations
COPY packages packages
COPY apps apps
COPY scripts scripts
COPY storage/demo storage/demo

# Create storage directory with appropriate permissions
RUN mkdir -p /app/storage/raw /app/storage/exports /app/storage/demo && \
    chown -R agentiq:agentiq /app

USER agentiq

# Production environment defaults
ENV ENVIRONMENT=production
ENV API_PORT=8000
ENV API_HOST=0.0.0.0

# Expose HTTP port
EXPOSE 8000

# Health check probing root /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Production entrypoint using dynamic $PORT (compatible with Railway, Render, Fly.io)
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_demo_data.py && exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
