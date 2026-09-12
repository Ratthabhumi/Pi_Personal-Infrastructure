#!/usr/bin/env bash
# ==============================================================================
# SCRIPT: diagnose_victoriametrics.sh
# PURPOSE: Deep Forensic Diagnostics for VictoriaMetrics Target Discovery & Scrape Configuration
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}       VICTORIAMETRICS SCRAPE TARGET & CONFIG FORENSIC DIAGNOSTIC    ${NC}"
echo -e "${BLUE}======================================================================${NC}"

INFRA_DIR="${HOME}/Pi_Personal-Infrastructure"
if [ ! -d "$INFRA_DIR" ]; then
    INFRA_DIR="/data/docker/Pi_Personal-Infrastructure"
fi

# -----------------------------------------------------------------------------
# 1. Inspect Running Container Command, Image, Ports & Networks
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 1. Inspecting VictoriaMetrics Container State ===${NC}"
VM_STATUS=$(docker inspect victoriametrics --format '{{.State.Status}}' 2>/dev/null || echo "NOT_FOUND")
VM_IMAGE=$(docker inspect victoriametrics --format '{{.Config.Image}}' 2>/dev/null || echo "N/A")
VM_CMD=$(docker inspect victoriametrics --format '{{json .Config.Cmd}}' 2>/dev/null || echo "N/A")
VM_PORTS=$(docker inspect victoriametrics --format '{{json .NetworkSettings.Ports}}' 2>/dev/null || echo "N/A")
VM_NETWORKS=$(docker inspect victoriametrics --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}={{$v.IPAddress}} {{end}}' 2>/dev/null || echo "N/A")
VM_MOUNTS=$(docker inspect victoriametrics --format '{{json .Mounts}}' 2>/dev/null || echo "N/A")

echo -e "Status:           ${CYAN}${VM_STATUS}${NC}"
echo -e "Image:            ${CYAN}${VM_IMAGE}${NC}"
echo -e "Cmd:              ${CYAN}${VM_CMD}${NC}"
echo -e "Published Ports:  ${CYAN}${VM_PORTS}${NC}"
echo -e "Networks & IPs:   ${CYAN}${VM_NETWORKS}${NC}"
echo -e "Mounts:\n${VM_MOUNTS}" | jq . 2>/dev/null || echo "${VM_MOUNTS}"

# Determine primary bridge IP for host-to-container routing
VM_BRIDGE_IP=$(docker inspect victoriametrics --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{break}}{{end}}' 2>/dev/null || echo "")

# -----------------------------------------------------------------------------
# 2. Inspect Configuration File Actually Mounted Inside Container
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 2. Inspecting Mounted /etc/prometheus/prometheus.yml Inside Container ===${NC}"
# Use direct docker exec to avoid compose .env warnings on stderr
if docker exec victoriametrics test -f /etc/prometheus/prometheus.yml 2>/dev/null; then
    echo -e "${GREEN}[OK] /etc/prometheus/prometheus.yml exists inside container.${NC}"
    echo -e "\n--- Actual Content inside Container ---"
    docker exec victoriametrics cat /etc/prometheus/prometheus.yml
else
    echo -e "${RED}[FAIL] /etc/prometheus/prometheus.yml does NOT exist inside container!${NC}"
fi

# Compare host git file with /data production file
PROD_PROM="/data/docker/prometheus/config/prometheus.yml"
GIT_PROM="$INFRA_DIR/docker/prometheus/config/prometheus.yml"
echo -e "\n--- Host Configuration Comparison ---"
if [ -f "$GIT_PROM" ] && [ -f "$PROD_PROM" ]; then
    if cmp -s "$GIT_PROM" "$PROD_PROM"; then
        echo -e "${GREEN}[OK] $GIT_PROM matches $PROD_PROM identically.${NC}"
    else
        echo -e "${RED}[MISMATCH] $GIT_PROM differs from $PROD_PROM!${NC}"
        diff -u "$GIT_PROM" "$PROD_PROM" || true
    fi
fi

# -----------------------------------------------------------------------------
# 3. Check VictoriaMetrics Logs for Scraper & Config Activity
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 3. Recent VictoriaMetrics Logs (promscrape / scraper) ===${NC}"
docker logs victoriametrics --tail 100 2>&1 | grep -iE 'promscrape|scrape|config|error|fail|reload|acash|fatal' || echo "No promscrape keywords found in last 100 log lines."

# -----------------------------------------------------------------------------
# 4. Define Reachable Query Helper
# -----------------------------------------------------------------------------
# Port 8428 is not published to host 0.0.0.0 in compose.yaml.
# We test 3 query routes:
#   1. docker exec into container (127.0.0.1:8428)
#   2. host route to container bridge IP (${VM_BRIDGE_IP}:8428)
#   3. host localhost:8428 fallback
vm_query() {
    local path="$1"
    local res=""
    # Route 1: docker exec
    res=$(docker exec victoriametrics wget -qO- "http://127.0.0.1:8428${path}" 2>/dev/null || true)
    if [ -n "$res" ]; then
        echo "$res"
        return 0
    fi
    # Route 2: bridge IP
    if [ -n "$VM_BRIDGE_IP" ]; then
        res=$(curl -s "http://${VM_BRIDGE_IP}:8428${path}" 2>/dev/null || true)
        if [ -n "$res" ]; then
            echo "$res"
            return 0
        fi
    fi
    # Route 3: localhost fallback
    curl -s "http://localhost:8428${path}" 2>/dev/null || true
}

echo -e "\n${YELLOW}=== 4. Testing Query Reachability across Routes ===${NC}"
echo -n "Route 1 (docker exec 127.0.0.1:8428): "
R1_TEST=$(docker exec victoriametrics wget -qO- http://127.0.0.1:8428/metrics 2>/dev/null | head -n 1 || true)
if [ -n "$R1_TEST" ]; then echo -e "${GREEN}REACHABLE${NC} (${R1_TEST})"; else echo -e "${RED}UNREACHABLE${NC}"; fi

echo -n "Route 2 (host to bridge IP ${VM_BRIDGE_IP}:8428): "
if [ -n "$VM_BRIDGE_IP" ]; then
    R2_TEST=$(curl -s "http://${VM_BRIDGE_IP}:8428/metrics" 2>/dev/null | head -n 1 || true)
    if [ -n "$R2_TEST" ]; then echo -e "${GREEN}REACHABLE${NC} (${R2_TEST})"; else echo -e "${RED}UNREACHABLE${NC}"; fi
else
    echo "N/A (No bridge IP)"
fi

echo -n "Route 3 (host localhost:8428): "
R3_TEST=$(curl -s http://localhost:8428/metrics 2>/dev/null | head -n 1 || true)
if [ -n "$R3_TEST" ]; then echo -e "${GREEN}REACHABLE${NC}"; else echo -e "${YELLOW}UNREACHABLE (Port 8428 intentionally not published on host)${NC}"; fi

# -----------------------------------------------------------------------------
# 5. Query VictoriaMetrics Target & Build Info Endpoints
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 5. Querying Target Discovery & Build Info Endpoints ===${NC}"

echo -e "\n${CYAN}--- A. /api/v1/status/buildinfo ---${NC}"
BUILD_INFO=$(vm_query "/api/v1/status/buildinfo")
echo "$BUILD_INFO" | jq . 2>/dev/null || echo "${BUILD_INFO:-Failed}"

echo -e "\n${CYAN}--- B. GET /api/v1/targets (Raw JSON & Schema Analysis) ---${NC}"
RAW_TARGETS=$(vm_query "/api/v1/targets")
if [ -n "$RAW_TARGETS" ]; then
    echo "JSON parsed successfully."
    echo "$RAW_TARGETS" | jq '{status: .status, data_keys: (.data | keys)}' 2>/dev/null || echo "Keys inspection failed"
    
    echo -e "\nActive Targets:"
    echo "$RAW_TARGETS" | jq '.data.activeTargets[] | {job: .labels.job, scrapePool: .scrapePool, health: .health, scrapeUrl: .scrapeUrl, lastError: .lastError, lastScrape: .lastScrape}' 2>/dev/null || echo "No .data.activeTargets found"
    
    echo -e "\nAlternative Targets (if present):"
    echo "$RAW_TARGETS" | jq '.data.targets[] | {job: .labels.job, state: .state, scrapeUrl: .scrapeUrl, lastError: .lastError, lastScrape: .lastScrape}' 2>/dev/null || echo "No .data.targets found"
else
    echo -e "${RED}Failed to retrieve /api/v1/targets!${NC}"
fi

echo -e "\n${CYAN}--- C. GET /targets (HTML UI Endpoint Check) ---${NC}"
TARGETS_HTML=$(vm_query "/targets")
if [[ "$TARGETS_HTML" =~ "acash" ]]; then
    echo -e "${GREEN}[FOUND] 'acash' mentioned in /targets HTML endpoint!${NC}"
    echo "$TARGETS_HTML" | grep -iC 2 "acash" | head -n 20 || true
else
    echo "No 'acash' mention in /targets HTML output."
fi

echo -e "\n${CYAN}--- D. PromQL Discovery: up query ---${NC}"
UP_QUERY=$(vm_query "/api/v1/query?query=up")
echo "$UP_QUERY" | jq '.data.result[] | {metric: .metric, value: .value}' 2>/dev/null || echo "Failed to query PromQL up"

echo -e "\n${CYAN}--- E. PromQL acash-paper up query ---${NC}"
ACASH_UP_QUERY=$(vm_query "/api/v1/query?query=up%7Bjob=%22acash-paper%22%7D")
echo "$ACASH_UP_QUERY" | jq . 2>/dev/null || echo "Failed to query up{job='acash-paper'}"

# -----------------------------------------------------------------------------
# 6. VictoriaMetrics Scraper Internal Telemetry
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 6. VictoriaMetrics Scraper Internal Telemetry (/metrics) ===${NC}"
VM_METRICS=$(vm_query "/metrics")
echo "$VM_METRICS" | grep -E '^vm_promscrape_' || echo "No vm_promscrape metrics found in /metrics"

# -----------------------------------------------------------------------------
# 7. Test Config Reload Endpoint
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 7. Testing Config Reload Trigger ===${NC}"
if [ -n "$VM_BRIDGE_IP" ]; then
    RELOAD_RESP=$(curl -s -w "\nHTTP_STATUS: %{http_code}\n" -X POST "http://${VM_BRIDGE_IP}:8428/-/reload" 2>/dev/null || true)
else
    RELOAD_RESP=$(docker exec victoriametrics wget -qO- --post-data="" "http://127.0.0.1:8428/-/reload" 2>/dev/null || echo "Reload failed")
fi
echo "POST /-/reload response:"
echo "$RELOAD_RESP"

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}                     DIAGNOSTIC COMPLETE                              ${NC}"
echo -e "${BLUE}======================================================================${NC}"
