#!/usr/bin/env bash
# ──────────────────────────────────────────────────
#  EduPulse — MySQL Database Backup Script
# ──────────────────────────────────────────────────
#  Usage:
#    ./scripts/backup.sh                    # Local backup
#    UPLOAD_S3=true ./scripts/backup.sh     # Backup + upload to S3
# ──────────────────────────────────────────────────
set -euo pipefail

# ── Configuration ──
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CONTAINER_NAME="${CONTAINER_NAME:-edupulse-db}"
MYSQL_USER="${MYSQL_USER:-edupulse}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-edupulse_secret}"
MYSQL_DATABASE="${MYSQL_DATABASE:-edupulse}"
UPLOAD_S3="${UPLOAD_S3:-false}"
S3_BUCKET="${S3_BUCKET:-edupulse-backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="edupulse_backup_${TIMESTAMP}.sql.gz"

# ── Colours ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[BACKUP]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[BACKUP]${NC}  $1"; }
log_error() { echo -e "${RED}[BACKUP]${NC}  $1"; }

# ── Create backup directory ──
mkdir -p "$BACKUP_DIR"

# ── Perform dump ──
log_info "Starting MySQL backup: ${MYSQL_DATABASE} ..."
docker exec "$CONTAINER_NAME" \
    mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --databases "$MYSQL_DATABASE" \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
log_info "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# ── Upload to S3 (optional) ──
if [ "$UPLOAD_S3" = "true" ]; then
    log_info "Uploading to s3://${S3_BUCKET}/backups/${BACKUP_FILE} ..."
    aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/backups/${BACKUP_FILE}"
    log_info "S3 upload complete."
fi

# ── Cleanup old local backups ──
OLD_COUNT=$(find "$BACKUP_DIR" -name "edupulse_backup_*.sql.gz" -mtime +"$RETENTION_DAYS" | wc -l)
if [ "$OLD_COUNT" -gt 0 ]; then
    log_warn "Removing ${OLD_COUNT} backup(s) older than ${RETENTION_DAYS} days ..."
    find "$BACKUP_DIR" -name "edupulse_backup_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
fi

# ── Summary ──
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "edupulse_backup_*.sql.gz" | wc -l)
log_info "Backup complete. Total local backups: ${TOTAL_BACKUPS}"
log_info "Backup location: ${BACKUP_DIR}/${BACKUP_FILE}"
