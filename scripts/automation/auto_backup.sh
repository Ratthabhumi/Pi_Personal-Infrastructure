#!/usr/bin/env bash
# ==============================================================================
# AUTONOMOUS SRE SNAPSHOT & RECOVERY ENGINE
# Location: scripts/automation/auto_backup.sh
# Performs live read-only volume backups and automated log/snapshot retention
# ==============================================================================

set -e # Exit immediately on any execution failure

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_ROOT="${HOME}/homelab_backups"
TARGET_DIR="${BACKUP_ROOT}/snapshot_${TIMESTAMP}"
RETENTION_DAYS=7

echo "==================================================================="
echo "   🛡️ HOMELAB AUTONOMOUS DATA SNAPSHOT & BACKUP ENGINE            "
echo "==================================================================="
echo "[1/4] Initializing backup target directory -> ${TARGET_DIR}..."
mkdir -p "${TARGET_DIR}/volumes"
mkdir -p "${TARGET_DIR}/configs"

# 1. Backup local workspace Git & declarative configuration configs
echo "[2/4] Archiving declarative IaC repository state..."
tar --exclude='.git' --exclude='victoriametrics-data' -czvf "${TARGET_DIR}/configs/iac_repository_${TIMESTAMP}.tar.gz" -C "$(pwd)" . > /dev/null
echo "  -> [OK] Infrastructure repository state archived."

# 2. Safely backup active Docker named volumes using ephemeral Alpine worker
echo "[3/4] Performing read-only hot-snapshots of active Docker named volumes..."
VOLUMES=("portainer_core_data" "grafana_observability_data")

for vol in "${VOLUMES[@]}"; do
    if docker volume inspect "$vol" &> /dev/null; then
        echo "  -> Capturing live snapshot of Docker volume: $vol..."
        docker run --rm -v "${vol}:/volume:ro" -v "${TARGET_DIR}/volumes:/backup" alpine:latest \
            tar -czvf "/backup/${vol}.tar.gz" -C /volume . > /dev/null
        echo "  -> [OK] Volume '$vol' snapshot preserved."
    else
        echo "  -> [Notice] Volume '$vol' not detected in current engine; skipping."
    fi
done

# 3. Compile master archive & enforce disk retention policy
echo "[4/4] Compressing final payload & executing SRE retention governance..."
cd "${BACKUP_ROOT}"
tar -czvf "homelab_backup_${TIMESTAMP}.tar.gz" "snapshot_${TIMESTAMP}" > /dev/null
rm -rf "snapshot_${TIMESTAMP}" # Remove temporary uncompressed working staging folder

# Retain only snapshots younger than RETENTION_DAYS to protect SSD storage health
echo "  -> Pruning historical archives older than ${RETENTION_DAYS} days..."
find "${BACKUP_ROOT}" -name "homelab_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete

FINAL_SIZE=$(du -sh "${BACKUP_ROOT}/homelab_backup_${TIMESTAMP}.tar.gz" | awk '{print $1}')
echo "==================================================================="
echo "   ✅ BACKUP SUCCESSFUL | Archive Size: ${FINAL_SIZE}             "
echo "   📁 Path: ${BACKUP_ROOT}/homelab_backup_${TIMESTAMP}.tar.gz     "
echo "==================================================================="
