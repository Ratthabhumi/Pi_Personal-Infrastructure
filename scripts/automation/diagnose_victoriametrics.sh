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
# 1. Inspect Running Container Command, Image & Mounts
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 1. Inspecting VictoriaMetrics Container State ===${NC}"
VM_STATUS=$(docker inspect victoriametrics --format '{{.State.Status}}' 2>/dev/null || echo "NOT_FOUND")
VM_IMAGE=$(docker inspect victoriametrics --format '{{.Config.Image}}' 2>/dev/null || echo "N/A")
VM_CMD=$(docker inspect victoriametrics --format '{{json .Config.Cmd}}' 2>/dev/null || echo "N/A")
VM_MOUNTS=$(docker inspect victoriametrics --format '{{json .Mounts}}' 2>/dev/null || echo "N/A")
VM_NETWORKS=$(docker inspect victoriametrics --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || echo "N/A")

echo -e "Status:   ${CYAN}${VM_STATUS}${NC}"
echo -e "Image:    ${CYAN}${VM_IMAGE}${NC}"
echo -e "Cmd:      ${CYAN}${VM_CMD}${NC}"
echo -e "Networks: ${CYAN}${VM_NETWORKS}${NC}"
echo -e "Mounts:\n${VM_MOUNTS}" | jq . 2>/dev/null || echo "${VM_MOUNTS}"

# -----------------------------------------------------------------------------
# 2. Inspect Configuration File Actually Mounted Inside Container
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 2. Inspecting Mounted /etc/prometheus/prometheus.yml Inside Container ===${NC}"
cd "$INFRA_DIR/docker"
if docker compose exec victoriametrics test -f /etc/prometheus/prometheus.yml 2>/dev/null; then
    echo -e "${GREEN}[OK] /etc/prometheus/prometheus.yml exists inside container.${NC}"
    echo -e "\n--- Actual Content inside Container ---"
    docker compose exec victoriametrics cat /etc/prometheus/prometheus.yml
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
# 4. Query VictoriaMetrics Target Endpoints
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 4. Querying Target Discovery Endpoints ===${NC}"

echo -e "\n${CYAN}--- A. GET /api/v1/targets (Raw JSON Sample) ---${NC}"
RAW_TARGETS=$(curl -s http://localhost:8428/api/v1/targets 2>/dev/null || echo "{}")
echo "$RAW_TARGETS" | jq '{status: .status, data_keys: (.data | keys)}' 2>/dev/null || echo "Failed to parse /api/v1/targets JSON"

echo -e "\n${CYAN}--- B. Active Targets in /api/v1/targets ---${NC}"
# Check if activeTargets exists (standard Prometheus)
ACTIVE_TARGETS=$(echo "$RAW_TARGETS" | jq -r '.data.activeTargets // empty' 2>/dev/null || true)
if [ -n "$ACTIVE_TARGETS" ] && [ "$ACTIVE_TARGETS" != "null" ]; then
    echo -e "${GREEN}[FOUND] .data.activeTargets present (${#ACTIVE_TARGETS} chars):${NC}"
    echo "$RAW_TARGETS" | jq '.data.activeTargets[] | {job: .labels.job, scrapePool: .scrapePool, health: .health, scrapeUrl: .scrapeUrl, lastError: .lastError, lastScrape: .lastScrape}' 2>/dev/null || true
else
    echo "No .data.activeTargets found."
fi

# Check if targets exists (alternative VictoriaMetrics)
ALT_TARGETS=$(echo "$RAW_TARGETS" | jq -r '.data.targets // empty' 2>/dev/null || true)
if [ -n "$ALT_TARGETS" ] && [ "$ALT_TARGETS" != "null" ]; then
    echo -e "${GREEN}[FOUND] .data.targets present:${NC}"
    echo "$RAW_TARGETS" | jq '.data.targets[] | {job: .labels.job, state: .state, scrapeUrl: .scrapeUrl, lastError: .lastError, lastScrape: .lastScrape}' 2>/dev/null || true
else
    echo "No .data.targets found."
fi

echo -e "\n${CYAN}--- C. GET /targets (HTML UI Endpoint Check) ---${NC}"
TARGETS_HTML=$(curl -s http://localhost:8428/targets 2>/dev/null || true)
if [[ "$TARGETS_HTML" =~ "acash" ]]; then
    echo -e "${GREEN}[FOUND] 'acash' mentioned in /targets HTML endpoint!${NC}"
else
    echo "No 'acash' mention in /targets HTML output."
fi

echo -e "\n${CYAN}--- D. PromQL Discovery: up query ---${NC}"
UP_QUERY=$(curl -s 'http://localhost:8428/api/v1/query?query=up' 2>/dev/null || echo "{}")
echo "$UP_QUERY" | jq '.data.result[] | {metric: .metric, value: .value}' 2>/dev/null || echo "Failed to query PromQL up"

echo -e "\n${CYAN}--- E. PromQL acash-paper up query ---${NC}"
ACASH_UP_QUERY=$(curl -s 'http://localhost:8428/api/v1/query?query=up%7Bjob=%22acash-paper%22%7D' 2>/dev/null || echo "{}")
echo "$ACASH_UP_QUERY" | jq . 2>/dev/null || echo "Failed to query up{job='acash-paper'}"

# -----------------------------------------------------------------------------
# 5. VictoriaMetrics Scraper Internal Telemetry
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 5. VictoriaMetrics Scraper Internal Telemetry (/metrics) ===${NC}"
curl -s http://localhost:8428/metrics 2>/dev/null | grep -E '^vm_promscrape_' || echo "No vm_promscrape metrics found in /metrics"

# -----------------------------------------------------------------------------
# 6. Test Config Reload Endpoint
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}=== 6. Testing Config Reload Trigger ===${NC}"
RELOAD_RESP=$(curl -s -w "\nHTTP_STATUS: %{http_code}\n" -X POST http://localhost:8428/-/reload 2>/dev/null || true)
echo "POST /-/reload response:"
echo "$RELOAD_RESP"

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}                     DIAGNOSTIC COMPLETE                              ${NC}"
echo -e "${BLUE}======================================================================${NC}"
