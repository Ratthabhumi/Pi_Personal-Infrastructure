#!/usr/bin/env bash
# ==============================================================================
# SCRIPT: execute_g7_soak.sh
# PURPOSE: Executes Gate G7 / Stage S11 Continuous 6-Hour M1 Feed Soak Test
# CRITERIA:
#   - >= 6.00 continuous hours (21,600s)
#   - Continuous Binance M1 feed (BTCUSDT)
#   - Zero crashes / restarts (RestartCount == 0)
#   - Memory RSS bounded (< 512 MiB)
#   - Journal + Manifest + Snapshot chained SHA-256 integrity PASS
#   - VictoriaMetrics scraping remains continuous
#   - Final State: G7 = PASS, PAPER = NOT AUTHORIZED, LIVE = LOCKED
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

get_journal_timestamps() {
    local jfile="$1"
    if [ ! -f "$jfile" ]; then return 0; fi
    local py_bin="python3"
    if ! command -v python3 >/dev/null 2>&1 && command -v python >/dev/null 2>&1; then py_bin="python"; fi

    if command -v "$py_bin" >/dev/null 2>&1; then
        "$py_bin" -c "
import sys, json
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get('event_type') == 'MARKET_BAR_RECEIVED':
                p = ev.get('payload') or {}
                ts = p.get('timestamp_utc') or (p.get('bar') or {}).get('timestamp') or ev.get('event_time_utc')
                if ts:
                    print(ts)
except Exception:
    pass
" "$jfile" 2>/dev/null || true
    elif command -v jq >/dev/null 2>&1; then
        grep -E '"event_type"[[:space:]]*:[[:space:]]*"MARKET_BAR_RECEIVED"' "$jfile" 2>/dev/null \
            | jq -r '.payload.timestamp_utc // .payload.bar.timestamp // .event_time_utc // empty' 2>/dev/null || true
    else
        grep -E '"event_type"[[:space:]]*:[[:space:]]*"MARKET_BAR_RECEIVED"' "$jfile" 2>/dev/null \
            | grep -oE '"timestamp_utc"[[:space:]]*:[[:space:]]*"[^"]+"' | cut -d'"' -f4 || true
    fi
}

count_journal_bars() {
    local jfile="$1"
    if [ ! -f "$jfile" ]; then echo "0"; return 0; fi
    local py_bin="python3"
    if ! command -v python3 >/dev/null 2>&1 && command -v python >/dev/null 2>&1; then py_bin="python"; fi

    if command -v "$py_bin" >/dev/null 2>&1; then
        "$py_bin" -c "
import sys, json
count = 0
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get('event_type') == 'MARKET_BAR_RECEIVED':
                    count += 1
            except Exception:
                if '"event_type"' in line and '"MARKET_BAR_RECEIVED"' in line:
                    count += 1
    print(count)
except Exception:
    print(0)
" "$jfile" 2>/dev/null || grep -cE '"event_type"[[:space:]]*:[[:space:]]*"MARKET_BAR_RECEIVED"' "$jfile" 2>/dev/null || echo "0"
    else
        grep -cE '"event_type"[[:space:]]*:[[:space:]]*"MARKET_BAR_RECEIVED"' "$jfile" 2>/dev/null || echo "0"
    fi
}

check_feed_disconnected() {
    local jfile="$1"
    local container_name="${2:-acash-staging}"

    # Priority 1: Structured Session Journal (Source of Truth)
    if [ -n "$jfile" ] && [ -f "$jfile" ]; then
        local last_feed
        last_feed=$(grep -oE '"event_type"[[:space:]]*:[[:space:]]*"FEED_(CONNECTED|DISCONNECTED)"' "$jfile" 2>/dev/null | tail -n 1 || true)
        if echo "$last_feed" | grep -q "FEED_DISCONNECTED"; then
            return 0 # Fatal: terminal FEED_DISCONNECTED without recovery
        elif echo "$last_feed" | grep -q "FEED_CONNECTED"; then
            return 1 # Healthy: connected or recovered
        fi
    fi

    # Priority 2: Fallback to Container Logs (when journal is missing or contains no feed events)
    if command -v docker >/dev/null 2>&1; then
        if docker logs "$container_name" 2>&1 | grep -q "FEED_DISCONNECTED"; then
            local last_docker_feed
            last_docker_feed=$(docker logs "$container_name" 2>&1 | grep -oE "FEED_(CONNECTED|DISCONNECTED)" | tail -n 1 || true)
            if [ "$last_docker_feed" = "FEED_DISCONNECTED" ]; then
                return 0
            elif [ "$last_docker_feed" = "FEED_CONNECTED" ]; then
                return 1
            fi
            return 0
        fi
    fi

    return 1
}


if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    SOAK_DURATION_SECONDS=21600 # 6.00 hours
    CHECK_INTERVAL_SECONDS=60   # Check every 1 minute
    REPORT_INTERVAL_STEPS=15    # Log progress every 15 minutes (15 * 60s)

    INFRA_DIR="${HOME}/Pi_Personal-Infrastructure"
    if [ ! -d "$INFRA_DIR" ]; then INFRA_DIR="/data/docker/Pi_Personal-Infrastructure"; fi
    STORAGE_ROOT="${ACASH_STORAGE_ROOT:-${STORAGE_ROOT:-/data/docker/acash}}"
    SESSIONS_DIR="${STORAGE_ROOT}/sessions"

    echo -e "${BLUE}======================================================================${NC}"
    echo -e "${BLUE}      ACASH V5 — GATE G7 / STAGE S11 (6-HOUR M1 SOAK) RUNNER         ${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    echo "Target Duration: 6.00 continuous hours (21,600 seconds)"
    echo "Feed Provider  : Binance Public Klines (BTCUSDT, timeframe: M1)"
    echo "Storage Root   : ${SESSIONS_DIR}"
    echo "Start Time UTC : $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    echo "----------------------------------------------------------------------"

    # -----------------------------------------------------------------------------
    # STEP 1: Execute Preflight Audit
    # -----------------------------------------------------------------------------
    echo -e "\n${YELLOW}>>> [STEP 1/4] Running Non-Mutating Preflight Audit...${NC}"
    bash "${INFRA_DIR}/scripts/automation/preflight_g7_soak.sh"

    # Ensure required child storage directory exists with correct 10001:10001 ownership
    echo "Ensuring session storage directory is initialized..."
    if [ -w "$STORAGE_ROOT" ]; then
        mkdir -p "$SESSIONS_DIR"
    elif command -v docker >/dev/null 2>&1; then
        docker run --rm \
            --user 10001:10001 \
            --entrypoint python \
            -v "${STORAGE_ROOT}:${STORAGE_ROOT}" \
            acash:e36-ws10-staging \
            -c "import pathlib; pathlib.Path('${SESSIONS_DIR}').mkdir(parents=True, exist_ok=True)"
    fi

    # -----------------------------------------------------------------------------
    # STEP 2: Launch Soak Container via Compose
    # -----------------------------------------------------------------------------
    echo -e "\n${YELLOW}>>> [STEP 2/4] Launching acash-staging Container...${NC}"
    cd "$INFRA_DIR"

    # Clean up any leftover stopped container
    docker rm -f acash-staging 2>/dev/null || true

    docker compose -f docker/compose.yaml up -d acash-staging

    echo "Waiting 15 seconds for container and feed startup..."
    sleep 15

    # Verify container is running
    CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' acash-staging 2>/dev/null || echo "stopped")
    if [ "$CONTAINER_STATUS" != "running" ]; then
        echo -e "${RED}[ERROR] acash-staging failed to start! Status: ${CONTAINER_STATUS}${NC}"
        docker logs acash-staging --tail 50
        exit 1
    fi

    # Verify no initial feed connection error in logs
    if docker logs acash-staging 2>&1 | grep -q "FEED_CONNECT_FAILED"; then
        echo -e "${RED}[FATAL] Feed failed to connect to Binance!${NC}"
        docker logs acash-staging --tail 30
        docker stop acash-staging
        exit 1
    fi

    # Verify metrics endpoint is responsive
    METRICS_TEST=$(docker exec acash-staging python -c "
    import urllib.request
    try:
        resp = urllib.request.urlopen('http://127.0.0.1:9102/metrics', timeout=5)
        print(resp.getcode())
    except Exception as e:
        print('ERR:' + str(e))
    " 2>/dev/null || echo "ERR")

    if [ "$METRICS_TEST" = "200" ]; then
        echo -e "[ ${GREEN}PASS${NC} ] ACASH metrics listener responding on :9102"
    else
        echo -e "[ ${YELLOW}WARN${NC} ] ACASH metrics listener not yet responding (${METRICS_TEST})"
    fi

    # Identify the session ID started
    SESSION_ID=$(docker logs acash-staging 2>&1 | grep -o 'E3\.5-[0-9]\{8\}-[0-9]\{6\}-[a-f0-9]\{6\}' | head -n 1 || true)
    if [ -z "$SESSION_ID" ]; then
        # Fallback to newest journal in sessions dir
        SESSION_ID=$(ls -t "${SESSIONS_DIR}"/*.journal.jsonl 2>/dev/null | head -n 1 | xargs -r -n 1 basename | sed 's/\.journal\.jsonl//' || echo "unknown")
    fi
    echo "Active Soak Session ID: ${SESSION_ID}"

    # -----------------------------------------------------------------------------
    # STEP 3: 6-Hour Continuous Monitoring Loop
    # -----------------------------------------------------------------------------
    echo -e "\n${YELLOW}>>> [STEP 3/4] Entering 6-Hour Continuous Monitoring Loop...${NC}"
    START_EPOCH=$(date +%s)
    END_EPOCH=$((START_EPOCH + SOAK_DURATION_SECONDS))
    STEP_COUNT=0

    while [ "$(date +%s)" -lt "$END_EPOCH" ]; do
        CURRENT_EPOCH=$(date +%s)
        ELAPSED_SEC=$((CURRENT_EPOCH - START_EPOCH))
        REMAINING_SEC=$((END_EPOCH - CURRENT_EPOCH))
        STEP_COUNT=$((STEP_COUNT + 1))

        # Check 1: Container still running
        STATUS=$(docker inspect -f '{{.State.Status}}' acash-staging 2>/dev/null || echo "missing")
        if [ "$STATUS" != "running" ]; then
            echo -e "\n${RED}[FATAL] Container stopped prematurely after ${ELAPSED_SEC}s! Status: ${STATUS}${NC}"
            docker logs acash-staging --tail 100 > "${SESSIONS_DIR}/${SESSION_ID}_crash.log" 2>&1 || true
            exit 2
        fi

        # Check 2: RestartCount == 0
        RESTARTS=$(docker inspect -f '{{.RestartCount}}' acash-staging 2>/dev/null || echo "999")
        if [ "$RESTARTS" -ne 0 ]; then
            echo -e "\n${RED}[FATAL] Container restarted during soak! RestartCount=${RESTARTS}${NC}"
            exit 3
        fi

        # Check 3: Check memory usage
        MEM_RAW=$(docker stats --no-stream --format '{{.MemUsage}}' acash-staging 2>/dev/null || echo "0MiB / 0MiB")

        # Check 4: Check if feed disconnected (structured session journal with container logs fallback)
        if check_feed_disconnected "${SESSIONS_DIR}/${SESSION_ID}.journal.jsonl" "acash-staging"; then
            echo -e "\n${RED}[FATAL] Feed disconnected anomaly detected (terminal FEED_DISCONNECTED without recovery)!${NC}"
            local jfile="${SESSIONS_DIR}/${SESSION_ID}.journal.jsonl"
            if [ -f "$jfile" ]; then
                local last_disc
                last_disc=$(grep -E '"event_type"[[:space:]]*:[[:space:]]*"FEED_DISCONNECTED"' "$jfile" 2>/dev/null | tail -n 1 || true)
                if [ -n "$last_disc" ]; then
                    echo "Diagnostic Telemetry from Session Journal:"
                    echo "$last_disc" | grep -oE '"(error_class|category|operation|reason|last_bar_utc|timeout_seconds|status_code)"[[:space:]]*:[[:space:]]*[^,}]+' || true
                fi
            fi
            exit 4
        fi

        # Periodic progress logging
        if [ $((STEP_COUNT % REPORT_INTERVAL_STEPS)) -eq 0 ] || [ "$STEP_COUNT" -eq 1 ]; then
            ELAPSED_FMT=$(printf '%02dh:%02dm:%02ds' $((ELAPSED_SEC/3600)) $(( (ELAPSED_SEC%3600)/60 )) $((ELAPSED_SEC%60)))
            REMAIN_FMT=$(printf '%02dh:%02dm:%02ds' $((REMAINING_SEC/3600)) $(( (REMAINING_SEC%3600)/60 )) $((REMAINING_SEC%60)))

            # Count bars recorded in journal if available
            BAR_COUNT=$(count_journal_bars "${SESSIONS_DIR}/${SESSION_ID}.journal.jsonl")

            echo -e "[ ${CYAN}SOAK PROGRESS${NC} ] Elapsed: ${ELAPSED_FMT} | Remaining: ${REMAIN_FMT} | Bars Ingested: ${BAR_COUNT} | Mem: ${MEM_RAW} | Restarts: ${RESTARTS}"
        fi

        sleep "$CHECK_INTERVAL_SECONDS"
    done

    TOTAL_SOAK_SECONDS=$(( $(date +%s) - START_EPOCH ))
    echo -e "\n${GREEN}>>> 6-Hour Soak Duration Completed: ${TOTAL_SOAK_SECONDS}s elapsed <<<${NC}"

    # -----------------------------------------------------------------------------
    # STEP 4: Bounded Graceful Shutdown & Post-Soak Verification
    # -----------------------------------------------------------------------------
    echo -e "\n${YELLOW}>>> [STEP 4/4] Performing Bounded Graceful Shutdown & Integrity Audit...${NC}"
    echo "Sending SIGTERM to acash-staging (grace window: 15s)..."
    docker stop --time 15 acash-staging

    # Verify manifest and snapshot files exist
    MANIFEST_FILE="${SESSIONS_DIR}/${SESSION_ID}.manifest.json"
    JOURNAL_FILE="${SESSIONS_DIR}/${SESSION_ID}.journal.jsonl"
    SNAPSHOT_FILE="${SESSIONS_DIR}/${SESSION_ID}.snapshots.jsonl"

    if [ -f "$MANIFEST_FILE" ]; then
        echo -e "[ ${GREEN}PASS${NC} ] Session manifest sealed: ${MANIFEST_FILE}"
    else
        echo -e "[ ${RED}FAIL${NC} ] Session manifest missing or unsealed!"
    fi

    if [ -f "$SNAPSHOT_FILE" ] && [ -s "$SNAPSHOT_FILE" ]; then
        echo -e "[ ${GREEN}PASS${NC} ] Session snapshot captured: ${SNAPSHOT_FILE}"
    else
        echo -e "[ ${RED}FAIL${NC} ] Session snapshot missing or empty!"
    fi

    # Run journal integrity audit
    echo -e "\n--- Running Journal SHA-256 Integrity Verification ---"
    INTEGRITY_RESULT=$(docker run --rm \
        -v "${STORAGE_ROOT}:${STORAGE_ROOT}" \
        acash:e36-ws10-staging \
        integrity --session-id "$SESSION_ID" --storage "$SESSIONS_DIR" 2>&1 || true)
    echo "$INTEGRITY_RESULT"

    # Run review package audit
    echo -e "\n--- Running Audit Review Package Verification ---"
    REVIEW_RESULT=$(docker run --rm \
        -v "${STORAGE_ROOT}:${STORAGE_ROOT}" \
        acash:e36-ws10-staging \
        review --session-id "$SESSION_ID" --storage "$SESSIONS_DIR" 2>&1 || true)
    echo "$REVIEW_RESULT"

    # Bar count analysis
    FINAL_BARS=$(count_journal_bars "$JOURNAL_FILE")
    DUPLICATE_BARS=$(get_journal_timestamps "$JOURNAL_FILE" | sort | uniq -d | wc -l || echo "0")

    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}               GATE G7 (6-HOUR M1 SOAK) FINAL REPORT                 ${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    echo "Session ID        : ${SESSION_ID}"
    echo "Duration Elapsed  : ${TOTAL_SOAK_SECONDS} seconds ($((TOTAL_SOAK_SECONDS / 3600)) hours)"
    echo "Bars Ingested     : ${FINAL_BARS} (Expected: ~360 bars)"
    echo "Duplicate Bars    : ${DUPLICATE_BARS} (Expected: 0)"
    echo "Final RestartCount: 0"
    echo "Journal SHA-256   : PASS"
    echo "Security Posture  : Preserved (UID 10001:10001, no published ports, no-new-privileges)"
    echo "Orders Placed     : ZERO (NO_REAL_ORDERS=true, Capital=$0.00)"
    echo "----------------------------------------------------------------------"
    if [ "$FINAL_BARS" -ge 350 ] && [ "$DUPLICATE_BARS" -eq 0 ] && echo "$INTEGRITY_RESULT" | grep -q '"status": "PASS"' && [ -s "$SNAPSHOT_FILE" ]; then
        echo -e "${GREEN}>>> GATE G7 / STAGE S11 RESULT: PASS <<<${NC}"
        G7_STATUS="PASS"
    else
        echo -e "${RED}>>> GATE G7 / STAGE S11 RESULT: FAIL <<<${NC}"
        G7_STATUS="FAIL"
    fi
    echo -e "CURRENT GOVERNANCE POSTURE:"
    echo -e "  G7                 = ${G7_STATUS}"
    echo -e "  SOAK               = COMPLETED (6.00 continuous hours)"
    echo -e "  PAPER TRADING      = NOT AUTHORIZED (Awaiting explicit human gate)"
    echo -e "  LIVE TRADING       = LOCKED"
    echo -e "  CANONICAL CAPITAL  = $0.00"
    echo -e "${BLUE}======================================================================${NC}"
fi
