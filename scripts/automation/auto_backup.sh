#!/usr/bin/env bash

# ==============================================================================
# HOMELAB & ACASH SRE SNAPSHOT & RECOVERY ENGINE (E3.6 / WS10 Remediation)
# ==============================================================================

set -euo pipefail

LOCK_FILE="/var/lock/homelab_backup.lock"
sudo touch "${LOCK_FILE}" 2>/dev/null || true
exec 200>"${LOCK_FILE}"

if ! flock -n 200; then
    echo "❌ ERROR: Another backup process is already running. Aborting." >&2
    exit 1
fi

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_ROOT="/data/backups"
SOURCE_DIR="/data/docker"
RETENTION_DAYS="${HOMELAB_BACKUP_RETENTION_DAYS:-14}"
LOG_FILE="/var/log/homelab_backup.log"

log() {
    local msg="[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1"
    echo "${msg}"
    if [ -w "${LOG_FILE}" ] || sudo touch "${LOG_FILE}" 2>/dev/null; then
        echo "${msg}" | sudo tee -a "${LOG_FILE}" >/dev/null || true
    fi
}

log "==================================================================="
log "   HOMELAB & ACASH PRODUCTION DATA BACKUP ENGINE"
log "==================================================================="

sudo mkdir -p "${BACKUP_ROOT}"

ARCHIVE_FILE="${BACKUP_ROOT}/homelab_backup_${TIMESTAMP}.tar.gz"
CHECKSUM_FILE="${ARCHIVE_FILE}.sha256"

log "[1/4] Archiving production Docker state (/data/docker)..."

# IMPORTANT:
# - Exclude transient logs.
# - Exclude disposable ACASH restore-drill directories.
# - A tar exit code of 1 means files changed while being read.
#   That archive is NOT accepted as a verified backup.
set +e
sudo tar \
    --exclude='*/logs/*' \
    --exclude='docker/acash-ws10-restore-drill-*' \
    --exclude='docker/pgadmin/data/sessions' \
    --exclude='docker/victoriametrics/data/data/small' \
    -czf "${ARCHIVE_FILE}" \
    -C "/data" \
    "docker"
TAR_EXIT=$?
set -e

if [ "${TAR_EXIT}" -ne 0 ]; then
    log "❌ BACKUP FAILED: tar exited with code ${TAR_EXIT}."
    log "   Archive will NOT receive a checksum and will NOT be marked verified."
    exit 1
fi

log "[2/4] Verifying archive integrity..."

if ! sudo gzip -t "${ARCHIVE_FILE}"; then
    log "❌ BACKUP FAILED: gzip integrity check failed."
    exit 1
fi

if ! sudo tar -tzf "${ARCHIVE_FILE}" >/dev/null; then
    log "❌ BACKUP FAILED: tar archive integrity check failed."
    exit 1
fi

log "[3/4] Generating SHA-256 integrity checksum..."

(
    cd "${BACKUP_ROOT}"
    sudo sha256sum "$(basename "${ARCHIVE_FILE}")" |
        sudo tee "${CHECKSUM_FILE}" >/dev/null
)

log "   SHA-256 checksum created."

log "[4/4] Executing SRE retention governance..."
log "  -> Pruning historical archives older than ${RETENTION_DAYS} days..."

sudo find "${BACKUP_ROOT}" \
    -name "homelab_backup_*.tar.gz" \
    -mtime +"${RETENTION_DAYS}" \
    -delete

sudo find "${BACKUP_ROOT}" \
    -name "homelab_backup_*.tar.gz.sha256" \
    -mtime +"${RETENTION_DAYS}" \
    -delete

FINAL_SIZE=$(du -sh "${ARCHIVE_FILE}" | awk '{print $1}')
ARCHIVE_SHA=$(awk '{print $1}' "${CHECKSUM_FILE}")

log "==================================================================="
log "   BACKUP SUCCESSFUL & VERIFIED"
log "   Archive Size     : ${FINAL_SIZE}"
log "   Archive Path     : ${ARCHIVE_FILE}"
log "   SHA-256          : ${ARCHIVE_SHA}"
log "==================================================================="
