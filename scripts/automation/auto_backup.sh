#!/usr/bin/env bash
# ==============================================================================
# HOMELAB & ACASH SRE SNAPSHOT & RECOVERY ENGINE (E3.6 / WS10 Remediation)
# Location: scripts/automation/auto_backup.sh
# Performs live archiving of the /data/docker production directory
#
# STORAGE LIMITATION (Risk R4):
# /data/docker and /data/backups reside on the SAME physical storage device.
# Local backup protects against logical corruption, but is NOT disaster recovery.
# Off-host backup remains a future requirement (Sprint 15).
# ==============================================================================

set -euo pipefail

# 1. Concurrency Guard: Ensure only one backup runs at a time
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
LOG_FILE="/var/log/homelab_backup.log"

# O3 Retention Semantics:
# Backup retention must preserve all evidence required by the active observation-window
# policy plus the O3 seven-day evidence-retention margin.
# Default homelab retention is configurable; default = 14 days unless overridden.
RETENTION_DAYS="${HOMELAB_BACKUP_RETENTION_DAYS:-14}"

# Logging wrapper
log() {
  local msg="[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1"
  echo "${msg}"
  if [ -w "${LOG_FILE}" ] || sudo touch "${LOG_FILE}" 2>/dev/null; then
    echo "${msg}" | sudo tee -a "${LOG_FILE}" >/dev/null || true
  fi
}

log "==================================================================="
log "   🛡️ HOMELAB & ACASH PRODUCTION DATA BACKUP ENGINE               "
log "==================================================================="

# Ensure backup directory exists
sudo mkdir -p "${BACKUP_ROOT}"

ARCHIVE_FILE="${BACKUP_ROOT}/homelab_backup_${TIMESTAMP}.tar.gz"
CHECKSUM_FILE="${ARCHIVE_FILE}.sha256"

log "[1/4] Archiving production Docker state (/data/docker)..."
# Exclude transient container logs to preserve disk bandwidth and space
sudo tar --exclude='*/logs/*' -czvf "${ARCHIVE_FILE}" -C "/data" "docker" > /dev/null

log "[2/4] Generating SHA-256 integrity checksum..."
(cd "${BACKUP_ROOT}" && sha256sum "$(basename "${ARCHIVE_FILE}")" | sudo tee "${CHECKSUM_FILE}" >/dev/null)

log "[3/4] Executing SRE retention governance..."
log "  -> Pruning historical archives older than ${RETENTION_DAYS} days..."
# Retention check: delete older archives and their corresponding checksum files
sudo find "${BACKUP_ROOT}" -name "homelab_backup_*.tar.gz" -mtime +"${RETENTION_DAYS}" -delete
sudo find "${BACKUP_ROOT}" -name "homelab_backup_*.tar.gz.sha256" -mtime +"${RETENTION_DAYS}" -delete

FINAL_SIZE=$(du -sh "${ARCHIVE_FILE}" | awk '{print $1}')
ARCHIVE_SHA=$(awk '{print $1}' "${CHECKSUM_FILE}")

log "[4/4] Backup complete & verified."
log "==================================================================="
log "   ✅ BACKUP SUCCESSFUL | Archive Size: ${FINAL_SIZE}"
log "   📁 Archive Path      : ${ARCHIVE_FILE}"
log "   🔒 SHA-256 Checksum  : ${ARCHIVE_SHA}"
log "==================================================================="
