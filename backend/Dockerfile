# ──────────────────────────────────────────────
#  EduPulse Backend — Multi-stage Dockerfile
# ──────────────────────────────────────────────

# ---------- Stage 1: Builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system deps required for mysqlclient / pymysql compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim AS runtime

# Install only the runtime libs needed by mysqlclient
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-libmysqlclient-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -r edupulse && useradd -r -g edupulse -d /app -s /sbin/nologin edupulse

WORKDIR /app

# Copy application code
COPY . .

# Copy entrypoint script and make executable
COPY ../scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh 2>/dev/null || true

# Own the app directory
RUN chown -R edupulse:edupulse /app

USER edupulse

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command — overridden by docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
