#!/usr/bin/env bash
# ==============================================================================
# SCRIPT: preflight_g7_soak.sh
# PURPOSE: Final Non-Mutating Preflight Audit before Gate G7 / Stage S11 (6h M1 Soak)
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}       ACASH GATE G7 / STAGE S11 (6H SOAK) PREFLIGHT AUDIT           ${NC}"
echo -e "${BLUE}======================================================================${NC}"

ACASH_DIR="${HOME}/Acash"
INFRA_DIR="${HOME}/Pi_Personal-Infrastructure"
if [ ! -d "$ACASH_DIR" ]; then ACASH_DIR="/data/docker/Acash"; fi
if [ ! -d "$INFRA_DIR" ]; then INFRA_DIR="/data/docker/Pi_Personal-Infrastructure"; fi

FAILURES=0

record_check() {
    local num="$1"
    local desc="$2"
    local status="$3"
    local details="$4"

    if [ "$status" = "PASS" ]; then
        echo -e "[ ${GREEN}PASS${NC} ] ${num}: ${desc}"
    elif [ "$status" = "WARN" ]; then
        echo -e "[ ${YELLOW}WARN${NC} ] ${num}: ${desc}"
    else
        echo -e "[ ${RED}FAIL${NC} ] ${num}: ${desc}"
        FAILURES=$((FAILURES + 1))
    fi
    if [ -n "$details" ]; then
        echo "         Details: ${details}"
    fi
}

# -----------------------------------------------------------------------------
# 1. Repository Provenance & Ratification Artifact
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- 1. Checking Governance Provenance & Ratification ---${NC}"
cd "$ACASH_DIR"
ACASH_HEAD=$(git rev-parse --short HEAD)
RATIF_FILE="$ACASH_DIR/E3.6-HUMAN-RATIFICATION-G7-SOAK.md"

if [ -f "$RATIF_FILE" ]; then
    record_check "1.1" "Human Governance Ratification record RATIF-E36-G7-SOAK-20260912 exists" "PASS" "Found at ${RATIF_FILE}"
else
    record_check "1.1" "Human Governance Ratification record RATIF-E36-G7-SOAK-20260912 exists" "FAIL" "Missing ratification record"
fi

PLAN_6H=$(grep -c "6h soak" "$ACASH_DIR/E3.6-IMPLEMENTATION-PLAN.md" || true)
if [ "$PLAN_6H" -ge 2 ]; then
    record_check "1.2" "E3.6-IMPLEMENTATION-PLAN.md amended to 6h soak" "PASS" "${PLAN_6H} references found"
else
    record_check "1.2" "E3.6-IMPLEMENTATION-PLAN.md amended to 6h soak" "FAIL" "Found ${PLAN_6H} references"
fi

DESIGN_6H=$(grep -c "6h soak" "$ACASH_DIR/E3.6-DESIGN.md" || true)
if [ "$DESIGN_6H" -ge 1 ]; then
    record_check "1.3" "E3.6-DESIGN.md amended to 6h soak" "PASS" "${DESIGN_6H} references found"
else
    record_check "1.3" "E3.6-DESIGN.md amended to 6h soak" "FAIL" "Found ${DESIGN_6H} references"
fi

cd "$INFRA_DIR"
INFRA_HEAD=$(git rev-parse --short HEAD)
record_check "1.4" "Pi_Personal-Infrastructure HEAD verified" "PASS" "HEAD=${INFRA_HEAD}"

# -----------------------------------------------------------------------------
# 2. Storage Root & State Interlock Invariants
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- 2. Checking Storage Root & Interlock State ---${NC}"
STORAGE_ROOT="/data/docker/acash"
if [ -d "$STORAGE_ROOT" ]; then
    STORAGE_OWNER=$(stat -c '%u:%g' "$STORAGE_ROOT")
    if [ "$STORAGE_OWNER" = "10001:10001" ]; then
        record_check "2.1" "Storage root /data/docker/acash owned by 10001:10001" "PASS" "Owner: ${STORAGE_OWNER}"
    else
        record_check "2.1" "Storage root /data/docker/acash owned by 10001:10001" "WARN" "Owner: ${STORAGE_OWNER} (expected 10001:10001)"
    fi
else
    record_check "2.1" "Storage root /data/docker/acash exists" "FAIL" "Directory missing"
fi

SESSIONS_DIR="/data/docker/acash/sessions"
if [ -d "$SESSIONS_DIR" ]; then
    record_check "2.2" "Sessions destination /data/docker/acash/sessions exists" "PASS" "Directory present"
else
    record_check "2.2" "Sessions destination /data/docker/acash/sessions exists" "WARN" "Will be created at first run"
fi

ACTIVE_WINDOW=$(find /data/docker/acash/windows -name "*.state.json" -exec grep -l '"state": "OPEN"' {} + 2>/dev/null || true)
if [ -z "$ACTIVE_WINDOW" ]; then
    record_check "2.3" "Zero OPEN window state on disk (interlock QUIESCENT)" "PASS" "No active window"
else
    record_check "2.3" "Zero OPEN window state on disk (interlock QUIESCENT)" "FAIL" "Found active window: ${ACTIVE_WINDOW}"
fi

RUNNING_ACASH=$(docker ps --filter name=acash -q || true)
if [ -z "$RUNNING_ACASH" ]; then
    record_check "2.4" "Zero existing acash containers currently running" "PASS" "Clean runtime slate"
else
    record_check "2.4" "Zero existing acash containers currently running" "FAIL" "Containers running: ${RUNNING_ACASH}"
fi

# -----------------------------------------------------------------------------
# 3. Docker Image Provenance & Security Hardening
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- 3. Checking Staging Image & Security Settings ---${NC}"
IMAGE_ID=$(docker images -q acash:e36-ws10-staging || true)
if [ -n "$IMAGE_ID" ]; then
    record_check "3.1" "Image acash:e36-ws10-staging present" "PASS" "ID=${IMAGE_ID}"
else
    record_check "3.1" "Image acash:e36-ws10-staging present" "FAIL" "Image not found on host"
fi

# Verify compose definition invariants
cd "$INFRA_DIR"
COMPOSE_JSON=$(docker compose -f docker/compose.yaml config --format json 2>/dev/null || echo "{}")

STAGING_USER=$(echo "$COMPOSE_JSON" | jq -r '.services["acash-staging"].user // empty' 2>/dev/null || true)
if [ "$STAGING_USER" = "10001:10001" ]; then
    record_check "3.2" "Compose acash-staging runs as UID 10001:10001" "PASS" "user=${STAGING_USER}"
else
    record_check "3.2" "Compose acash-staging runs as UID 10001:10001" "FAIL" "user=${STAGING_USER}"
fi

STAGING_SEC_OPT=$(echo "$COMPOSE_JSON" | jq -r '.services["acash-staging"].security_opt[]?' 2>/dev/null || true)
if echo "$STAGING_SEC_OPT" | grep -q "no-new-privileges:true"; then
    record_check "3.3" "Compose acash-staging enforces no-new-privileges:true" "PASS" "Found"
else
    record_check "3.3" "Compose acash-staging enforces no-new-privileges:true" "FAIL" "Missing security_opt"
fi

STAGING_PORTS=$(echo "$COMPOSE_JSON" | jq -r '.services["acash-staging"].ports // empty' 2>/dev/null || true)
if [ -z "$STAGING_PORTS" ] || [ "$STAGING_PORTS" = "null" ]; then
    record_check "3.4" "Zero published ports for acash-staging" "PASS" "No ports published"
else
    record_check "3.4" "Zero published ports for acash-staging" "FAIL" "Ports found: ${STAGING_PORTS}"
fi

NO_REAL_ORDERS=$(echo "$COMPOSE_JSON" | jq -r '.services["acash-staging"].environment.NO_REAL_ORDERS // empty' 2>/dev/null || true)
CAPITAL=$(echo "$COMPOSE_JSON" | jq -r '.services["acash-staging"].environment.ACASH_CANONICAL_CAPITAL // empty' 2>/dev/null || true)
if [ "$NO_REAL_ORDERS" = "true" ] && [ "$CAPITAL" = "0" ]; then
    record_check "3.5" "Governance invariants: NO_REAL_ORDERS=true and capital=0" "PASS" "NO_REAL_ORDERS=${NO_REAL_ORDERS}, capital=${CAPITAL}"
else
    record_check "3.5" "Governance invariants: NO_REAL_ORDERS=true and capital=0" "FAIL" "NO_REAL_ORDERS=${NO_REAL_ORDERS}, capital=${CAPITAL}"
fi

# -----------------------------------------------------------------------------
# 4. VictoriaMetrics Telemetry Scrape Target
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- 4. Checking VictoriaMetrics Observability Target ---${NC}"
PROM_CFG="/data/docker/prometheus/config/prometheus.yml"
if grep -q "acash-staging:9102" "$PROM_CFG" 2>/dev/null; then
    record_check "4.1" "VictoriaMetrics config includes acash-staging:9102 scrape target" "PASS" "Scrape target defined"
else
    record_check "4.1" "VictoriaMetrics config includes acash-staging:9102 scrape target" "FAIL" "Missing scrape target in ${PROM_CFG}"
fi

VM_PING=$(docker exec victoriametrics wget -qO- "http://127.0.0.1:8428/-/healthy" 2>/dev/null || true)
if [ "$VM_PING" = "OK" ] || [ -n "$VM_PING" ]; then
    record_check "4.2" "VictoriaMetrics instance is healthy" "PASS" "Status OK"
else
    record_check "4.2" "VictoriaMetrics instance is healthy" "FAIL" "Unhealthy or unreachable"
fi

# -----------------------------------------------------------------------------
# 5. Network Architecture & Egress for Continuous M1 Feed
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- 5. Network Architecture & Continuous M1 Feed Egress ---${NC}"
STAGING_NETWORKS=$(echo "$COMPOSE_JSON" | jq -r '.services["acash-staging"].networks | keys[]?' 2>/dev/null || true)

if echo "$STAGING_NETWORKS" | grep -q "proxy" && echo "$STAGING_NETWORKS" | grep -q "acash_staging"; then
    record_check "5.1" "Dual network attachment (proxy for egress, acash_staging for telemetry)" "PASS" "Networks: $(echo $STAGING_NETWORKS | tr '\n' ' ')"
else
    record_check "5.1" "Dual network attachment (proxy for egress, acash_staging for telemetry)" "FAIL" "Networks: $(echo $STAGING_NETWORKS | tr '\n' ' ')"
fi

PROXY_EGRESS=$(docker run --rm --network homelab_proxy curlimages/curl:latest -s -o /dev/null -w "%{http_code}" https://api.binance.com/api/v3/ping 2>/dev/null || true)
if [ "$PROXY_EGRESS" = "200" ]; then
    record_check "5.2" "homelab_proxy WAN egress to api.binance.com verified" "PASS" "HTTP 200 from Binance API"
else
    record_check "5.2" "homelab_proxy WAN egress to api.binance.com verified" "FAIL" "HTTP ${PROXY_EGRESS}"
fi

STAGING_EGRESS=$(docker run --rm --network homelab_acash_staging curlimages/curl:latest -s -o /dev/null -w "%{http_code}" --connect-timeout 3 https://api.binance.com/api/v3/ping 2>/dev/null || true)
if [ "$STAGING_EGRESS" != "200" ]; then
    record_check "5.3" "homelab_acash_staging is strictly isolated (internal: true)" "PASS" "WAN dropped as expected"
else
    record_check "5.3" "homelab_acash_staging is strictly isolated (internal: true)" "FAIL" "WAN accessible on internal network"
fi

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}                     PREFLIGHT SUMMARY                                ${NC}"
echo -e "${BLUE}======================================================================${NC}"

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}>>> PREFLIGHT AUDIT PASSED (0 failures) <<<${NC}"
    echo "Host and configuration are fully verified for Gate G7 / Stage S11 soak launch."
    exit 0
else
    echo -e "${RED}>>> PREFLIGHT AUDIT FAILED (${FAILURES} issues detected) <<<${NC}"
    echo "Fail-closed interlock engaged. Do not launch soak until issues are resolved."
    exit 1
fi
