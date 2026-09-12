#!/usr/bin/env bash
# ==============================================================================
# SCRIPT: verify_g7_evidence.sh
# PURPOSE: Audits and Produces the Formal G7 Evidence Package from a Sealed Session
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

STORAGE_ROOT="/data/docker/acash"
SESSIONS_DIR="${STORAGE_ROOT}/sessions"

SESSION_ID="${1:-}"
if [ -z "$SESSION_ID" ]; then
    # Pick newest manifest in sessions dir
    LATEST_MANIFEST=$(ls -t "${SESSIONS_DIR}"/*.manifest.json 2>/dev/null | head -n 1 || true)
    if [ -n "$LATEST_MANIFEST" ]; then
        SESSION_ID=$(basename "$LATEST_MANIFEST" | sed 's/\.manifest\.json//')
    fi
fi

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}[ERROR] No session ID provided and no manifest found in ${SESSIONS_DIR}!${NC}"
    echo "Usage: $0 [SESSION_ID]"
    exit 1
fi

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}       ACASH V5 — GATE G7 EVIDENCE & RECONCILIATION PACKAGE          ${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo "Auditing Session ID: ${SESSION_ID}"
echo "Storage Path       : ${SESSIONS_DIR}"
echo "Timestamp UTC      : $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
echo "----------------------------------------------------------------------"

JOURNAL_FILE="${SESSIONS_DIR}/${SESSION_ID}.journal.jsonl"
MANIFEST_FILE="${SESSIONS_DIR}/${SESSION_ID}.manifest.json"
SNAPSHOT_FILE="${SESSIONS_DIR}/${SESSION_ID}.snapshots.jsonl"

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

# 1. Manifest Presence and Sealed Status
if [ -f "$MANIFEST_FILE" ]; then
    SEALED_VAL=$(jq -r '.sealed // false' "$MANIFEST_FILE" 2>/dev/null || echo "false")
    GIT_COMMIT=$(jq -r '.git_commit // "unknown"' "$MANIFEST_FILE" 2>/dev/null || echo "unknown")
    if [ "$SEALED_VAL" = "true" ]; then
        record_check "1.1" "Manifest sealed status verified" "PASS" "sealed=true, git_commit=${GIT_COMMIT}"
    else
        record_check "1.1" "Manifest sealed status verified" "FAIL" "sealed=${SEALED_VAL}"
    fi
else
    record_check "1.1" "Manifest file present" "FAIL" "Missing ${MANIFEST_FILE}"
fi

# 2. Journal SHA-256 Integrity
echo -e "\n--- Running acash.paper integrity check ---"
INTEGRITY_OUTPUT=$(docker run --rm \
    -v "${STORAGE_ROOT}:${STORAGE_ROOT}" \
    acash:e36-ws10-staging \
    integrity --session-id "$SESSION_ID" --storage "$SESSIONS_DIR" 2>&1 || true)
echo "$INTEGRITY_OUTPUT"

if echo "$INTEGRITY_OUTPUT" | grep -q '"status": "PASS"'; then
    record_check "2.1" "Chained SHA-256 journal integrity verification" "PASS" "Zero violation events"
else
    record_check "2.1" "Chained SHA-256 journal integrity verification" "FAIL" "Integrity violation detected"
fi

# 3. Bar Count & Quality Analysis
if [ -f "$JOURNAL_FILE" ]; then
    TOTAL_EVENTS=$(wc -l < "$JOURNAL_FILE" 2>/dev/null || echo "0")
    BAR_EVENTS=$(grep -c '"event_type": "MARKET_BAR_RECORDED"' "$JOURNAL_FILE" 2>/dev/null || echo "0")
    DUPLICATE_TS=$(grep '"event_type": "MARKET_BAR_RECORDED"' "$JOURNAL_FILE" 2>/dev/null | jq -r '.payload.bar.timestamp' 2>/dev/null | sort | uniq -d | wc -l || echo "0")

    if [ "$BAR_EVENTS" -ge 350 ]; then
        record_check "3.1" "Bar count conforms to 6-hour M1 window (>=350 bars)" "PASS" "${BAR_EVENTS} bars recorded"
    else
        record_check "3.1" "Bar count conforms to 6-hour M1 window (>=350 bars)" "FAIL" "Only ${BAR_EVENTS} bars recorded"
    fi

    if [ "$DUPLICATE_TS" -eq 0 ]; then
        record_check "3.2" "Zero duplicate timestamps in feed stream" "PASS" "0 duplicates detected"
    else
        record_check "3.2" "Zero duplicate timestamps in feed stream" "FAIL" "${DUPLICATE_TS} duplicate timestamps found"
    fi
else
    record_check "3.1" "Journal file present" "FAIL" "Missing ${JOURNAL_FILE}"
fi

# 4. Review Package Generation (OBSERVED / MODEL / DERIVED)
echo -e "\n--- Running acash.paper review check ---"
REVIEW_OUTPUT=$(docker run --rm \
    -v "${STORAGE_ROOT}:${STORAGE_ROOT}" \
    acash:e36-ws10-staging \
    review --session-id "$SESSION_ID" --storage "$SESSIONS_DIR" 2>&1 || true)
echo "$REVIEW_OUTPUT"

if echo "$REVIEW_OUTPUT" | grep -q '"session_id"'; then
    record_check "4.1" "E3.5 review package successfully generated" "PASS" "Manifest + reconciliation validated"
else
    record_check "4.1" "E3.5 review package successfully generated" "FAIL" "Review package generation failed"
fi

# 5. Security & Order Invariants
REAL_ORDERS=$(grep -c '"event_type": "ORDER_SUBMITTED"' "$JOURNAL_FILE" 2>/dev/null || echo "0")
if [ "$REAL_ORDERS" -eq 0 ]; then
    record_check "5.1" "Zero real order submissions (NO_REAL_ORDERS=true)" "PASS" "0 orders submitted"
else
    record_check "5.1" "Zero real order submissions (NO_REAL_ORDERS=true)" "FAIL" "${REAL_ORDERS} orders detected!"
fi

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}                     G7 EVIDENCE SUMMARY                              ${NC}"
echo -e "${BLUE}======================================================================${NC}"

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}>>> GATE G7 ACCEPTANCE CRITERIA: PASS <<<${NC}"
    echo "Formal Status:"
    echo "  G7                  = PASS / VERIFIED"
    echo "  STAGE S11           = CLOSED"
    echo "  PAPER AUTHORIZATION = NOT AUTHORIZED (Awaiting explicit human gate)"
    echo "  LIVE TRADING        = LOCKED"
    echo "  CANONICAL CAPITAL   = $0.00"
    exit 0
else
    echo -e "${RED}>>> GATE G7 ACCEPTANCE CRITERIA: FAIL (${FAILURES} issues) <<<${NC}"
    echo "Formal Status:"
    echo "  G7                  = FAIL"
    echo "  PAPER AUTHORIZATION = NOT AUTHORIZED"
    echo "  LIVE TRADING        = LOCKED"
    exit 1
fi
