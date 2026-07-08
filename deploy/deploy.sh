#!/usr/bin/env bash
# ──────────────────────────────────────────────────
#  EduPulse — Deployment Script
# ──────────────────────────────────────────────────
#  Deploys the latest version to an EC2 instance.
#
#  Usage:
#    ./deploy/deploy.sh                 # Deploy to production
#    ./deploy/deploy.sh --skip-build    # Skip Docker build
# ──────────────────────────────────────────────────
set -euo pipefail

# ── Configuration (override via environment) ──
EC2_HOST="${EC2_HOST:?Set EC2_HOST to your server's Elastic IP or hostname}"
EC2_USER="${EC2_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-~/.ssh/edupulse-key.pem}"
APP_DIR="${APP_DIR:-~/EduPulse}"
BRANCH="${BRANCH:-main}"

SKIP_BUILD=false
if [[ "${1:-}" == "--skip-build" ]]; then
    SKIP_BUILD=true
fi

# ── Colours ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[DEPLOY]${NC} $1"; }
log_error() { echo -e "${RED}[DEPLOY]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC}   $1"; }

# ── SSH helper ──
remote_exec() {
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "$@"
}

# ── Main ──
main() {
    echo ""
    log_info "=========================================="
    log_info "  EduPulse Deployment"
    log_info "  Target: ${EC2_USER}@${EC2_HOST}"
    log_info "  Branch: ${BRANCH}"
    log_info "=========================================="
    echo ""

    # Step 1: Pull latest code
    log_step "1/5 — Pulling latest code from ${BRANCH} ..."
    remote_exec "cd ${APP_DIR} && git fetch origin && git checkout ${BRANCH} && git pull origin ${BRANCH}"

    # Step 2: Build (optional)
    if [ "$SKIP_BUILD" = false ]; then
        log_step "2/5 — Building Docker images ..."
        remote_exec "cd ${APP_DIR} && docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache"
    else
        log_step "2/5 — Skipping build (--skip-build flag)"
    fi

    # Step 3: Deploy
    log_step "3/5 — Starting services ..."
    remote_exec "cd ${APP_DIR} && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"

    # Step 4: Wait for health
    log_step "4/5 — Waiting for API to be healthy ..."
    local max_attempts=15
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if remote_exec "curl -sf http://localhost/api/v1/health > /dev/null 2>&1"; then
            log_info "API is healthy! ✓"
            break
        fi
        log_warn "Health check attempt ${attempt}/${max_attempts} ..."
        attempt=$((attempt + 1))
        sleep 5
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "API health check failed after ${max_attempts} attempts!"
        log_error "Check logs: ssh -i ${SSH_KEY} ${EC2_USER}@${EC2_HOST} 'cd ${APP_DIR} && docker compose logs api'"
        exit 1
    fi

    # Step 5: Show status
    log_step "5/5 — Deployment status:"
    remote_exec "cd ${APP_DIR} && docker compose ps"

    echo ""
    log_info "=========================================="
    log_info "  Deployment Complete! ✓"
    log_info "  URL: http://${EC2_HOST}"
    log_info "=========================================="
    echo ""
}

main "$@"
