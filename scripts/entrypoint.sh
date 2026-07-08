#!/usr/bin/env bash
# ──────────────────────────────────────────────
#  EduPulse — Container Entrypoint Script
# ──────────────────────────────────────────────
set -euo pipefail

# ── Colours for logging ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Wait for MySQL to accept connections ──
wait_for_db() {
    local host="${DB_HOST:-db}"
    local port="${DB_PORT:-3306}"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for MySQL at ${host}:${port} ..."

    while [ $attempt -le $max_attempts ]; do
        if python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('${host}', ${port}))
    s.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
            log_info "MySQL is ready! (attempt ${attempt}/${max_attempts})"
            return 0
        fi

        log_warn "MySQL not ready yet — attempt ${attempt}/${max_attempts}"
        attempt=$((attempt + 1))
        sleep 2
    done

    log_error "MySQL did not become ready after ${max_attempts} attempts. Exiting."
    exit 1
}

# ── Run database migrations ──
run_migrations() {
    log_info "Running Alembic migrations ..."
    cd /app
    python -m alembic upgrade head
    log_info "Migrations complete."
}

# ── Seed database (only if SEED_DB=true) ──
seed_database() {
    if [ "${SEED_DB:-false}" = "true" ]; then
        log_info "Seeding database ..."
        python -m app.db.seed
        log_info "Seeding complete."
    fi
}

# ── Main ──
main() {
    log_info "=== EduPulse Backend Starting ==="
    log_info "Environment: ${APP_ENV:-development}"

    # Wait for database if not using SQLite
    if [[ "${DATABASE_URL:-}" != sqlite* ]]; then
        wait_for_db
    fi

    # Run migrations
    run_migrations

    # Seed if requested
    seed_database

    # Start the application
    if [ "${APP_ENV:-development}" = "production" ]; then
        log_info "Starting Gunicorn with Uvicorn workers ..."
        exec gunicorn app.main:app \
            --worker-class uvicorn.workers.UvicornWorker \
            --workers "${GUNICORN_WORKERS:-4}" \
            --bind 0.0.0.0:8000 \
            --timeout 120 \
            --graceful-timeout 30 \
            --access-logfile - \
            --error-logfile -
    else
        log_info "Starting Uvicorn (development mode) ..."
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --reload
    fi
}

main "$@"
