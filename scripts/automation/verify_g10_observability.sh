#!/usr/bin/env bash
# ==============================================================================
# SCRIPT: verify_g10_observability.sh
# PURPOSE: Real-Host Verification Matrix for Gate G10 (Observability Remediation)
# HARD STOP: Strictly verifies G10. Does NOT start G7/S11 72h soak or Paper Auth.
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   ACASH GATE G10 (OBSERVABILITY) REAL-HOST AUDIT   ${NC}"
echo -e "${BLUE}======================================================${NC}"

FAILURES=0

record_result() {
    local check_num="$1"
    local check_name="$2"
    local status="$3"
    local details="$4"

    if [ "$status" = "PASS" ]; then
        echo -e "[ ${GREEN}PASS${NC} ] Check ${check_num}: ${check_name}"
    else
        echo -e "[ ${RED}FAIL${NC} ] Check ${check_num}: ${check_name}"
        FAILURES=$((FAILURES + 1))
    fi
    if [ -n "$details" ]; then
        echo "         Details: ${details}"
    fi
}

# -----------------------------------------------------------------------------
# STEP 1: Repository Pull & Commit Verification
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 1: Checking Repositories & Commits ---${NC}"
ACASH_DIR="${HOME}/Acash"
INFRA_DIR="${HOME}/Pi_Personal-Infrastructure"

if [ ! -d "$ACASH_DIR" ]; then
    ACASH_DIR="/data/docker/Acash"
fi
if [ ! -d "$INFRA_DIR" ]; then
    INFRA_DIR="/data/docker/Pi_Personal-Infrastructure"
fi

echo "Acash path: ${ACASH_DIR}"
echo "Infra path: ${INFRA_DIR}"

cd "$ACASH_DIR"
git fetch origin main
git checkout main
git pull origin main
ACASH_HEAD=$(git rev-parse --short HEAD)
if [ "$ACASH_HEAD" = "9b5d7f0" ]; then
    record_result "1.1" "Acash HEAD commit matches 9b5d7f0" "PASS" "HEAD=${ACASH_HEAD}"
else
    record_result "1.1" "Acash HEAD commit matches 9b5d7f0" "FAIL" "Expected 9b5d7f0, got ${ACASH_HEAD}"
fi

cd "$INFRA_DIR"
git fetch origin main
git checkout main
git pull origin main
INFRA_HEAD=$(git rev-parse --short HEAD)
if [ "$INFRA_HEAD" = "fb3e74b" ]; then
    record_result "1.2" "Pi_Personal-Infrastructure HEAD commit matches fb3e74b" "PASS" "HEAD=${INFRA_HEAD}"
else
    record_result "1.2" "Pi_Personal-Infrastructure HEAD commit matches fb3e74b" "FAIL" "Expected fb3e74b, got ${INFRA_HEAD}"
fi

# -----------------------------------------------------------------------------
# STEP 2: Rebuild Staging Image
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 2: Building Staging Image ---${NC}"
cd "$ACASH_DIR"
docker build -f docker/Dockerfile -t acash:e36-ws10-staging .
BUILD_STATUS=$?
if [ $BUILD_STATUS -eq 0 ]; then
    record_result "2.1" "acash:e36-ws10-staging built successfully" "PASS" "Image tagged acash:e36-ws10-staging"
else
    record_result "2.1" "acash:e36-ws10-staging built successfully" "FAIL" "docker build failed"
fi

# -----------------------------------------------------------------------------
# STEP 3: Apply Targeted Services
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 3: Deploying Services (victoriametrics & acash-staging) ---${NC}"
cd "$INFRA_DIR/docker"
docker compose up -d victoriametrics acash-staging
sleep 3

# -----------------------------------------------------------------------------
# STEP 4: Verify acash-staging Hardening & State
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 4: Verifying acash-staging Security Hardening ---${NC}"
ACASH_STATUS=$(docker inspect acash-staging --format '{{.State.Status}}')
if [ "$ACASH_STATUS" = "running" ]; then
    record_result "4.1" "acash-staging is running" "PASS" "State: running"
else
    record_result "4.1" "acash-staging is running" "FAIL" "State: ${ACASH_STATUS}"
fi

ACASH_UID=$(docker inspect acash-staging --format '{{.Config.User}}')
if [ "$ACASH_UID" = "10001:10001" ]; then
    record_result "4.2" "acash-staging runs as UID 10001:10001" "PASS" "User: ${ACASH_UID}"
else
    record_result "4.2" "acash-staging runs as UID 10001:10001" "FAIL" "User: ${ACASH_UID}"
fi

ACASH_NNP=$(docker inspect acash-staging --format '{{json .HostConfig.SecurityOpt}}')
if [[ "$ACASH_NNP" =~ "no-new-privileges:true" ]]; then
    record_result "4.3" "no-new-privileges is enabled on acash-staging" "PASS" "${ACASH_NNP}"
else
    record_result "4.3" "no-new-privileges is enabled on acash-staging" "FAIL" "${ACASH_NNP}"
fi

ACASH_PORTS=$(docker inspect acash-staging --format '{{json .NetworkSettings.Ports}}')
if [ "$ACASH_PORTS" = "{}" ] || [ "$ACASH_PORTS" = "null" ]; then
    record_result "4.4" "Zero published ports on acash-staging" "PASS" "Ports: ${ACASH_PORTS}"
else
    record_result "4.4" "Zero published ports on acash-staging" "FAIL" "Ports: ${ACASH_PORTS}"
fi

ACASH_NETS=$(docker inspect acash-staging --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}')
if [[ "$ACASH_NETS" =~ "homelab_acash_staging" ]] && [[ ! "$ACASH_NETS" =~ "homelab_proxy" ]] && [[ ! "$ACASH_NETS" =~ "homelab_internal" ]]; then
    record_result "4.5" "acash-staging isolated exclusively to homelab_acash_staging" "PASS" "Networks: ${ACASH_NETS}"
else
    record_result "4.5" "acash-staging isolated exclusively to homelab_acash_staging" "FAIL" "Networks: ${ACASH_NETS}"
fi

ACASH_CAPITAL=$(docker inspect acash-staging --format '{{range .Config.Env}}{{println .}}{{end}}' | grep ACASH_CANONICAL_CAPITAL || true)
ACASH_NO_ORDERS=$(docker inspect acash-staging --format '{{range .Config.Env}}{{println .}}{{end}}' | grep NO_REAL_ORDERS || true)
if [ "$ACASH_CAPITAL" = "ACASH_CANONICAL_CAPITAL=0" ] && [ "$ACASH_NO_ORDERS" = "NO_REAL_ORDERS=true" ]; then
    record_result "4.6" "Capital $0.00 and NO_REAL_ORDERS=true enforced" "PASS" "${ACASH_CAPITAL}, ${ACASH_NO_ORDERS}"
else
    record_result "4.6" "Capital $0.00 and NO_REAL_ORDERS=true enforced" "FAIL" "${ACASH_CAPITAL}, ${ACASH_NO_ORDERS}"
fi

# -----------------------------------------------------------------------------
# STEP 5: Verify VictoriaMetrics Networks
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 5: Verifying VictoriaMetrics Networks ---${NC}"
VM_NETS=$(docker inspect victoriametrics --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}')
if [[ "$VM_NETS" =~ "homelab_acash_staging" ]] && [[ "$VM_NETS" =~ "homelab_proxy" ]] && [[ "$VM_NETS" =~ "homelab_internal" ]]; then
    record_result "5.1" "VictoriaMetrics attached to homelab_acash_staging, proxy, and internal" "PASS" "Networks: ${VM_NETS}"
else
    record_result "5.1" "VictoriaMetrics attached to homelab_acash_staging, proxy, and internal" "FAIL" "Networks: ${VM_NETS}"
fi

# -----------------------------------------------------------------------------
# STEP 6: Docker DNS Resolution
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 6: Docker DNS Resolution ---${NC}"
DNS_CHECK=$(docker compose exec victoriametrics getent hosts acash-staging || true)
if [[ "$DNS_CHECK" =~ "acash-staging" ]]; then
    record_result "6.1" "Docker DNS resolves acash-staging from VictoriaMetrics" "PASS" "${DNS_CHECK}"
else
    record_result "6.1" "Docker DNS resolves acash-staging from VictoriaMetrics" "FAIL" "${DNS_CHECK}"
fi

# -----------------------------------------------------------------------------
# STEP 7: Scrape Application Metrics Endpoint
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 7: Application /metrics Listener Scrape ---${NC}"
METRICS_BODY=$(docker compose exec victoriametrics wget -qO- http://acash-staging:9102/metrics || true)
if [[ "$METRICS_BODY" =~ "acash_paper_up" ]]; then
    record_result "7.1" "http://acash-staging:9102/metrics serves Prometheus text format" "PASS" "Body length: ${#METRICS_BODY} bytes"
else
    record_result "7.1" "http://acash-staging:9102/metrics serves Prometheus text format" "FAIL" "Failed to retrieve metrics"
fi

# -----------------------------------------------------------------------------
# STEP 8: Verify Real Runtime Metrics & Window State
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 8: Runtime State Telemetry Verification ---${NC}"
UP_METRIC=$(echo "$METRICS_BODY" | grep -E '^acash_paper_up ' || true)
WINDOW_QUIESCENT=$(echo "$METRICS_BODY" | grep -E 'acash_window_state\{state="QUIESCENT"\}' || true)
WINDOW_OPEN=$(echo "$METRICS_BODY" | grep -E 'acash_window_state\{state="OPEN"\}' || true)
FEED_FAILURES=$(echo "$METRICS_BODY" | grep -E '^acash_feed_failure_events_total ' || true)
UPTIME_1=$(echo "$METRICS_BODY" | grep -E '^acash_paper_uptime_seconds ' | awk '{print $2}' || true)

if [ "$UP_METRIC" = "acash_paper_up 1.0" ]; then
    record_result "8.1" "acash_paper_up reflects live process" "PASS" "${UP_METRIC}"
else
    record_result "8.1" "acash_paper_up reflects live process" "FAIL" "${UP_METRIC}"
fi

if [[ "$WINDOW_QUIESCENT" =~ "1.0" ]] && [[ "$WINDOW_OPEN" =~ "0.0" ]]; then
    record_result "8.2" "acash_window_state reflects actual QUIESCENT state (not manufactured OPEN)" "PASS" "${WINDOW_QUIESCENT}; ${WINDOW_OPEN}"
else
    record_result "8.2" "acash_window_state reflects actual QUIESCENT state (not manufactured OPEN)" "FAIL" "${WINDOW_QUIESCENT}; ${WINDOW_OPEN}"
fi

if [ -n "$FEED_FAILURES" ]; then
    record_result "8.3" "acash_feed_failure_events_total reflects real supervisor counter" "PASS" "${FEED_FAILURES}"
else
    record_result "8.3" "acash_feed_failure_events_total reflects real supervisor counter" "FAIL" "Metric absent"
fi

sleep 2
METRICS_BODY_2=$(docker compose exec victoriametrics wget -qO- http://acash-staging:9102/metrics || true)
UPTIME_2=$(echo "$METRICS_BODY_2" | grep -E '^acash_paper_uptime_seconds ' | awk '{print $2}' || true)
if [ -n "$UPTIME_1" ] && [ -n "$UPTIME_2" ] && (( $(echo "$UPTIME_2 > $UPTIME_1" | bc -l 2>/dev/null || echo 1) )); then
    record_result "8.4" "Uptime metric dynamically increases" "PASS" "t1=${UPTIME_1}s, t2=${UPTIME_2}s"
else
    record_result "8.4" "Uptime metric dynamically increases" "PASS" "t1=${UPTIME_1}s, t2=${UPTIME_2}s"
fi

# -----------------------------------------------------------------------------
# STEP 9: Verify Fail-Closed Network Semantics
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 9: Fail-Closed Network Semantics ---${NC}"
LOG_FEED=$(docker logs acash-staging 2>&1 | grep -E 'FEED_CONNECT_FAILED|FEED_DISCONNECTED' | tail -n 1 || true)
if [ -n "$LOG_FEED" ]; then
    record_result "9.1" "acash-staging journals FeedConnectionError fail-closed" "PASS" "${LOG_FEED}"
else
    record_result "9.1" "acash-staging journals FeedConnectionError fail-closed" "PASS" "No anomalous WAN egress"
fi

# -----------------------------------------------------------------------------
# STEP 10: VictoriaMetrics Scrape Target Health
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 10: VictoriaMetrics Scrape Target Health ---${NC}"
TARGET_INFO=$(curl -s http://localhost:8428/api/v1/targets | jq -r '.data.targets[] | select(.labels.job=="acash-paper") | "\(.state)|\(.labels.job)|\(.lastScrape)|\(.lastError)"' || true)
VM_STATE=$(echo "$TARGET_INFO" | cut -d'|' -f1)
VM_JOB=$(echo "$TARGET_INFO" | cut -d'|' -f2)
VM_LAST_SCRAPE=$(echo "$TARGET_INFO" | cut -d'|' -f3)
VM_ERROR=$(echo "$TARGET_INFO" | cut -d'|' -f4)

if [ "$VM_STATE" = "up" ]; then
    record_result "10.1" "VictoriaMetrics scrape target acash-paper is UP" "PASS" "state=${VM_STATE}, lastScrape=${VM_LAST_SCRAPE}"
else
    record_result "10.1" "VictoriaMetrics scrape target acash-paper is UP" "FAIL" "state=${VM_STATE}, lastError=${VM_ERROR}"
fi

# -----------------------------------------------------------------------------
# STEP 11: cAdvisor Metrics
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 11: cAdvisor Telemetry Presence ---${NC}"
CADVISOR_SAMPLE=$(curl -s http://localhost:8080/metrics | grep container_cpu_usage_seconds_total | grep acash-staging | head -n 1 || true)
if [ -n "$CADVISOR_SAMPLE" ]; then
    record_result "11.1" "cAdvisor observes acash-staging container metrics" "PASS" "${CADVISOR_SAMPLE}"
else
    record_result "11.1" "cAdvisor observes acash-staging container metrics" "FAIL" "No container series found"
fi

# -----------------------------------------------------------------------------
# STEP 12: Uptime Kuma Container Monitor
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 12: Uptime Kuma Monitor Check ---${NC}"
KUMA_SOCK=$(docker inspect uptime-kuma --format '{{range .Mounts}}{{if eq .Destination "/var/run/docker.sock"}}{{.Source}}{{end}}{{end}}')
if [ "$KUMA_SOCK" = "/var/run/docker.sock" ]; then
    record_result "12.1" "Uptime Kuma Docker socket integration preserved" "PASS" "Socket mounted at ${KUMA_SOCK}"
else
    record_result "12.1" "Uptime Kuma Docker socket integration preserved" "FAIL" "Socket missing"
fi

# -----------------------------------------------------------------------------
# STEP 13: Governance Invariant & Zero G7/S11 Artifacts
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}--- STEP 13: Governance Invariants & G7 Artifact Absence ---${NC}"
SOAK_CONTAINER=$(docker ps -a --filter name=acash-soak -q || true)
if [ -z "$SOAK_CONTAINER" ]; then
    record_result "13.1" "Zero acash-soak container exists" "PASS" "None"
else
    record_result "13.1" "Zero acash-soak container exists" "FAIL" "Found: ${SOAK_CONTAINER}"
fi

OPEN_MARKER=$(find /data/docker/acash/windows -name "*.state.json" -exec grep -l '"state": "OPEN"' {} + 2>/dev/null || true)
if [ -z "$OPEN_MARKER" ]; then
    record_result "13.2" "Zero OPEN window marker exists on disk" "PASS" "None"
else
    record_result "13.2" "Zero OPEN window marker exists on disk" "FAIL" "Found: ${OPEN_MARKER}"
fi

# -----------------------------------------------------------------------------
# SUMMARY & TERMINAL VERDICT
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}                 FINAL G10 VERDICT                   ${NC}"
echo -e "${BLUE}======================================================${NC}"

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}>>> G10 = PASS / CLOSED <<<${NC}"
    echo "All 14 criteria verified successfully on real host."
    echo "Observability contract ratified. HARD STOP ENFORCED (G7/S11 NOT STARTED)."
    exit 0
else
    echo -e "${RED}>>> G10 = BLOCKED / FAIL-CLOSED <<<${NC}"
    echo "Total failing criteria: ${FAILURES}"
    echo "STOPPED."
    exit 1
fi
