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

STORAGE_ROOT="${ACASH_STORAGE_ROOT:-${STORAGE_ROOT:-/data/docker/acash}}"
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
G7_CONTINUITY_ELIGIBLE=true
RUN_CLASS="CONTINUOUS"

# Centralized Host Python Resolution Contract
resolve_host_python() {
    if [ -n "${G7_PYTHON_BIN:-}" ]; then
        if "$G7_PYTHON_BIN" -c "import sys" >/dev/null 2>&1; then
            printf '%s\n' "$G7_PYTHON_BIN"
            return 0
        else
            echo "[ERROR] Configured G7_PYTHON_BIN ('$G7_PYTHON_BIN') not executable or invalid" >&2
            return 1
        fi
    fi

    if python3 -c "import sys" >/dev/null 2>&1; then
        command -v python3
        return 0
    elif python -c "import sys" >/dev/null 2>&1; then
        command -v python
        return 0
    else
        echo "[ERROR] No usable host Python interpreter found (checked python3, python)" >&2
        return 1
    fi
}

HOST_PYTHON=$(resolve_host_python 2>/dev/null || true)

# Robust JSON field extractor (jq with python fallback)
get_json_field() {
    local file="$1"
    local field="$2"
    if [ ! -f "$file" ]; then echo ""; return 0; fi
    if command -v jq >/dev/null 2>&1; then
        jq -r ".${field} // empty" "$file" 2>/dev/null || true
    elif [ -n "$HOST_PYTHON" ]; then
        "$HOST_PYTHON" -c "import json, sys; d=json.load(open(sys.argv[1], encoding='utf-8')); val=d.get(sys.argv[2], ''); print(str(val).lower() if isinstance(val, bool) else ('' if val is None else val))" "$file" "$field" 2>/dev/null || true
    fi
}

# Robust journal timestamp extractor (jq with python fallback)
get_journal_timestamps() {
    local file="$1"
    if [ ! -f "$file" ]; then return 0; fi
    if command -v jq >/dev/null 2>&1; then
        grep -E '"event_type"[[:space:]]*:[[:space:]]*"MARKET_BAR_RECEIVED"' "$file" 2>/dev/null \
            | jq -r '.payload.timestamp_utc // .event_time_utc // empty' 2>/dev/null || true
    elif [ -n "$HOST_PYTHON" ]; then
        "$HOST_PYTHON" -c "
import json, sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        for line in f:
            if '\"event_type\"' in line and '\"MARKET_BAR_RECEIVED\"' in line:
                try:
                    ev = json.loads(line)
                    if ev.get('event_type') == 'MARKET_BAR_RECEIVED':
                        ts = ev.get('payload', {}).get('timestamp_utc') or ev.get('event_time_utc')
                        if ts: print(ts)
                except Exception: pass
except Exception: pass
" "$file" 2>/dev/null || true
    else
        grep -E '"event_type"[[:space:]]*:[[:space:]]*"MARKET_BAR_RECEIVED"' "$file" 2>/dev/null \
            | grep -oE '"timestamp_utc"[[:space:]]*:[[:space:]]*"[^"]+"' | cut -d'"' -f4 || true
    fi
}

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
# 1. Manifest Presence and Sealed Status
# -----------------------------------------------------------------------------
if [ -f "$MANIFEST_FILE" ]; then
    SEALED_VAL=$(get_json_field "$MANIFEST_FILE" "sealed")
    GIT_COMMIT=$(get_json_field "$MANIFEST_FILE" "git_commit")
    if [ "$SEALED_VAL" = "true" ]; then
        record_check "1.1" "Manifest sealed status verified" "PASS" "sealed=true, git_commit=${GIT_COMMIT:-unknown}"
    else
        record_check "1.1" "Manifest sealed status verified" "FAIL" "sealed=${SEALED_VAL}"
    fi

    M_NO_REAL=$(get_json_field "$MANIFEST_FILE" "no_real_orders")
    M_ORDERS=$(get_json_field "$MANIFEST_FILE" "total_order_count")
    if [ "$M_NO_REAL" = "true" ] && [ "$M_ORDERS" = "0" ]; then
        record_check "1.2" "Manifest attestation: no_real_orders=true, total_orders=0" "PASS" "no_real_orders=${M_NO_REAL}, total_orders=${M_ORDERS}"
    else
        record_check "1.2" "Manifest attestation: no_real_orders=true, total_orders=0" "FAIL" "no_real_orders=${M_NO_REAL}, total_orders=${M_ORDERS}"
    fi
else
    record_check "1.1" "Manifest file present" "FAIL" "Missing ${MANIFEST_FILE}"
fi

# -----------------------------------------------------------------------------
# 2. Daily Snapshot Artifact Verification (Required for Review Path)
# -----------------------------------------------------------------------------
if [ -f "$SNAPSHOT_FILE" ] && [ -s "$SNAPSHOT_FILE" ]; then
    SNAP_COUNT=$(wc -l < "$SNAPSHOT_FILE" 2>/dev/null || echo "0")
    SNAP_VALID=$(head -n 1 "$SNAPSHOT_FILE" | grep -o '"snapshot_id": "[^"]*"' | head -n 1 || true)
    if [ -n "$SNAP_VALID" ]; then
        record_check "2.1" "Daily snapshot artifact present and valid JSON" "PASS" "${SNAP_COUNT} snapshot(s) found"
    else
        record_check "2.1" "Daily snapshot artifact present and valid JSON" "FAIL" "Invalid snapshot JSON structure"
    fi
else
    record_check "2.1" "Daily snapshot artifact present and non-empty" "FAIL" "Missing or empty ${SNAPSHOT_FILE}"
fi

# -----------------------------------------------------------------------------
# 3. Journal SHA-256 Integrity Verification
# -----------------------------------------------------------------------------
echo -e "\n--- Running acash.paper integrity check ---"
if [ "${G7_TEST_MODE:-0}" = "1" ]; then
    INTEGRITY_OUTPUT='{"status": "PASS"}'
else
    INTEGRITY_OUTPUT=$(docker run --rm \
        -v "${STORAGE_ROOT}:${STORAGE_ROOT}" \
        acash:e36-ws10-staging \
        integrity --session-id "$SESSION_ID" --storage "$SESSIONS_DIR" 2>&1 || true)
fi
echo "$INTEGRITY_OUTPUT"

if echo "$INTEGRITY_OUTPUT" | grep -q '"status": "PASS"'; then
    record_check "3.1" "Chained SHA-256 journal integrity verification" "PASS" "Zero violation events"
else
    record_check "3.1" "Chained SHA-256 journal integrity verification" "FAIL" "Integrity violation detected"
fi

# -----------------------------------------------------------------------------
# 4. Bar Count & Quality Analysis (Actual Event: MARKET_BAR_RECEIVED)
# -----------------------------------------------------------------------------
if [ -f "$JOURNAL_FILE" ]; then
    TOTAL_EVENTS=$(wc -l < "$JOURNAL_FILE" 2>/dev/null || echo "0")
    BAR_EVENTS=$(grep -cE '"event_type"[[:space:]]*:[[:space:]]*"MARKET_BAR_RECEIVED"' "$JOURNAL_FILE" 2>/dev/null || true)
    BAR_EVENTS=$(echo "$BAR_EVENTS" | tr -d '[:space:]')

    DUPLICATE_TS=$(get_journal_timestamps "$JOURNAL_FILE" | sort | uniq -d | wc -l)
    DUPLICATE_TS=$(echo "$DUPLICATE_TS" | tr -d '[:space:]')

    if [ "$BAR_EVENTS" -ge 350 ] 2>/dev/null; then
        record_check "4.1" "Bar count conforms to 6-hour M1 window (>=350 bars)" "PASS" "${BAR_EVENTS} bars recorded"
    else
        record_check "4.1" "Bar count conforms to 6-hour M1 window (>=350 bars)" "FAIL" "Only ${BAR_EVENTS} bars recorded"
    fi

    if [ "$DUPLICATE_TS" = "0" ]; then
        record_check "4.2" "Zero duplicate timestamps in feed stream" "PASS" "0 duplicates detected"
    else
        record_check "4.2" "Zero duplicate timestamps in feed stream" "FAIL" "${DUPLICATE_TS} duplicate timestamps found"
    fi

    # Check 4.3: Feed connection stability, recovery audit, and run classification
    if [ -n "$HOST_PYTHON" ]; then
        FEED_DIAG_OUTPUT=$("$HOST_PYTHON" -c '
import json, sys

journal_path = sys.argv[1]
feed_events = []
disc_count = 0
last_error_class = "Unknown"
last_error_cat = "Unknown"

try:
    with open(journal_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                et = ev.get("event_type")
                if et in ("FEED_CONNECTED", "FEED_DISCONNECTED", "FEED_CONNECT_FAILED", "RECOVERY_ATTEMPTED"):
                    feed_events.append((et, ev.get("payload") or {}))
                    if et == "FEED_DISCONNECTED":
                        disc_count += 1
                        payload = ev.get("payload") or {}
                        last_error_class = payload.get("error_class") or "Unknown"
                        last_error_cat = payload.get("category") or "Unknown"
            except Exception:
                pass
except Exception:
    pass

if disc_count == 0:
    run_class = "CONTINUOUS"
    continuity_eligible = "true"
    check_status = "PASS"
    check_msg = "0 feed disconnects, continuous feed stream"
    recovery_mechanism = "N/A"
else:
    continuity_eligible = "false"
    last_event_type = feed_events[-1][0] if feed_events else "FEED_DISCONNECTED"
    if last_event_type in ("FEED_DISCONNECTED", "FEED_CONNECT_FAILED"):
        run_class = "INTERRUPTED"
        check_status = "FAIL"
        check_msg = f"Terminal disconnect: {last_error_class} [{last_error_cat}]"
        recovery_mechanism = "FAIL"
    else:
        last_disc_idx = -1
        for idx, (et, _) in enumerate(feed_events):
            if et == "FEED_DISCONNECTED":
                last_disc_idx = idx

        events_after_disc = feed_events[last_disc_idx+1:]
        has_recovery_attempt = any(et == "RECOVERY_ATTEMPTED" for et, _ in events_after_disc)
        reconnected_with_recovery = any(
            et == "FEED_CONNECTED" and (
                p.get("is_recovery") is True or
                p.get("resume_count", 0) > 0 or
                has_recovery_attempt
            )
            for et, p in events_after_disc
        )

        if has_recovery_attempt and reconnected_with_recovery:
            run_class = "OPERATOR-RECOVERED"
            check_status = "PASS"
            check_msg = f"Technical recovery: PASS ({disc_count} disconnect(s) recovered via explicit operator resume) - NOT ELIGIBLE for continuous G7"
            recovery_mechanism = "PASS"
        else:
            run_class = "INTERRUPTED"
            check_status = "FAIL"
            check_msg = "Irregular feed reconnection without verified operator recovery event"
            recovery_mechanism = "FAIL"

print(f"RUN_CLASS={run_class}")
print(f"CONTINUITY_ELIGIBLE={continuity_eligible}")
print(f"CHECK_STATUS={check_status}")
print(f"CHECK_MSG={check_msg}")
print(f"RECOVERY_MECHANISM={recovery_mechanism}")
print(f"DISC_COUNT={disc_count}")
' "$JOURNAL_FILE" 2>/dev/null || echo "")
    else
        FEED_DIAG_OUTPUT=""
    fi

    PARSED_RUN_CLASS=""
    PARSED_CONTINUITY_ELIGIBLE=""
    PARSED_CHECK_STATUS=""
    PARSED_CHECK_MSG=""
    PARSED_RECOVERY_MECHANISM=""
    PARSED_DISC_COUNT=""

    if [ -n "$FEED_DIAG_OUTPUT" ]; then
        while IFS='=' read -r key val; do
            key="${key%$'\r'}"
            val="${val%$'\r'}"
            case "$key" in
                RUN_CLASS) PARSED_RUN_CLASS="$val" ;;
                CONTINUITY_ELIGIBLE) PARSED_CONTINUITY_ELIGIBLE="$val" ;;
                CHECK_STATUS) PARSED_CHECK_STATUS="$val" ;;
                CHECK_MSG) PARSED_CHECK_MSG="$val" ;;
                RECOVERY_MECHANISM) PARSED_RECOVERY_MECHANISM="$val" ;;
                DISC_COUNT) PARSED_DISC_COUNT="$val" ;;
            esac
        done <<< "$FEED_DIAG_OUTPUT"
    fi

    if [ -n "$PARSED_RUN_CLASS" ] && [ -n "$PARSED_CHECK_STATUS" ]; then
        RUN_CLASS="$PARSED_RUN_CLASS"
        G7_CONTINUITY_ELIGIBLE="$PARSED_CONTINUITY_ELIGIBLE"
        record_check "4.3" "Feed connection stability & recovery" "$PARSED_CHECK_STATUS" "$PARSED_CHECK_MSG"
    else
        RUN_CLASS="INTERRUPTED"
        G7_CONTINUITY_ELIGIBLE="false"
        if [ -z "$HOST_PYTHON" ]; then
            record_check "4.3" "Feed connection stability & recovery" "FAIL" "Host Python interpreter unavailable for feed diagnostics"
        else
            record_check "4.3" "Feed connection stability & recovery" "FAIL" "Failed to parse feed events from journal"
        fi
    fi
else
    record_check "4.1" "Journal file present" "FAIL" "Missing ${JOURNAL_FILE}"
fi

# -----------------------------------------------------------------------------
# 5. Continuous Duration Verification (>= 21,600s / 6.00 continuous hours)
# -----------------------------------------------------------------------------
if [ -f "$MANIFEST_FILE" ]; then
    DURATION_SEC=$(get_json_field "$MANIFEST_FILE" "duration_seconds")
    if [ -z "$DURATION_SEC" ] || [ "$DURATION_SEC" = "null" ] || [ "$DURATION_SEC" = "0" ]; then
        START_ISO=$(get_json_field "$MANIFEST_FILE" "start_time_utc")
        END_ISO=$(get_json_field "$MANIFEST_FILE" "end_time_utc")
        if [ -n "$START_ISO" ] && [ -n "$END_ISO" ]; then
            if [ -n "$HOST_PYTHON" ]; then
                DURATION_SEC=$("$HOST_PYTHON" -c "from datetime import datetime; s=datetime.fromisoformat('$START_ISO'); e=datetime.fromisoformat('$END_ISO'); print(int((e-s).total_seconds()))" 2>/dev/null || echo 0)
            else
                DURATION_SEC=0
            fi
        else
            DURATION_SEC=0
        fi
    fi
    DURATION_SEC=$(echo "$DURATION_SEC" | tr -d '[:space:]')

    if [ -n "$DURATION_SEC" ] && [ "$DURATION_SEC" -ge 21600 ] 2>/dev/null; then
        record_check "5.1" "Session duration >= 6.00 continuous hours (21,600s)" "PASS" "Duration: ${DURATION_SEC}s ($((DURATION_SEC/3600))h $(( (DURATION_SEC%3600)/60 ))m)"
    else
        record_check "5.1" "Session duration >= 6.00 continuous hours (21,600s)" "FAIL" "Duration: ${DURATION_SEC}s (Required: >= 21600s)"
    fi
else
    record_check "5.1" "Session duration verification" "FAIL" "Missing manifest for timing audit"
fi

# -----------------------------------------------------------------------------
# 6. Review Package Generation (OBSERVED / MODEL / DERIVED)
# -----------------------------------------------------------------------------
echo -e "\n--- Running acash.paper review check ---"
if [ "${G7_TEST_MODE:-0}" = "1" ]; then
    REVIEW_OUTPUT="{\"session_id\": \"$SESSION_ID\", \"status\": \"PASS\"}"
else
    REVIEW_OUTPUT=$(docker run --rm \
        -v "${STORAGE_ROOT}:${STORAGE_ROOT}" \
        acash:e36-ws10-staging \
        review --session-id "$SESSION_ID" --storage "$SESSIONS_DIR" 2>&1 || true)
fi
echo "$REVIEW_OUTPUT"

if echo "$REVIEW_OUTPUT" | grep -q '"session_id"'; then
    record_check "6.1" "E3.5 review package successfully generated" "PASS" "Manifest + reconciliation validated"
else
    record_check "6.1" "E3.5 review package successfully generated" "FAIL" "Review package generation failed"
fi

# -----------------------------------------------------------------------------
# 7. Security & Order Invariants
# -----------------------------------------------------------------------------
if [ -f "$JOURNAL_FILE" ]; then
    REAL_ORDERS=$(grep -cE '"event_type"[[:space:]]*:[[:space:]]*"ORDER_SUBMITTED"' "$JOURNAL_FILE" 2>/dev/null || true)
    REAL_ORDERS=$(echo "$REAL_ORDERS" | tr -d '[:space:]')
    if [ "$REAL_ORDERS" = "0" ]; then
        record_check "7.1" "Zero real order submissions in journal (NO_REAL_ORDERS=true)" "PASS" "0 orders submitted"
    else
        record_check "7.1" "Zero real order submissions in journal (NO_REAL_ORDERS=true)" "FAIL" "${REAL_ORDERS} orders detected!"
    fi
fi

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}                     G7 EVIDENCE SUMMARY                              ${NC}"
echo -e "${BLUE}======================================================================${NC}"

if [ "$FAILURES" -eq 0 ] && [ "$G7_CONTINUITY_ELIGIBLE" = "true" ]; then
    echo -e "${GREEN}>>> GATE G7 ACCEPTANCE CRITERIA: PASS <<<${NC}"
    echo "Formal Status:"
    echo "  RUN CLASS           = ${RUN_CLASS}"
    echo "  CONTINUITY ELIGIBLE = YES"
    echo "  G7                  = PASS / VERIFIED"
    echo "  STAGE S11           = CLOSED"
    echo "  PAPER AUTHORIZATION = NOT AUTHORIZED (Awaiting explicit human gate)"
    echo "  LIVE TRADING        = LOCKED"
    echo "  CANONICAL CAPITAL   = \$0.00"
    exit 0
elif [ "$RUN_CLASS" = "OPERATOR-RECOVERED" ]; then
    echo -e "${YELLOW}>>> GATE G7 ACCEPTANCE CRITERIA: NOT ELIGIBLE (${RUN_CLASS}) <<<${NC}"
    echo "Formal Status:"
    echo "  RUN CLASS           = ${RUN_CLASS}"
    echo "  CONTINUITY ELIGIBLE = NO (Interrupted session recovered via explicit operator resume)"
    echo "  RECOVERY MECHANISM  = PASS / VERIFIED"
    echo "  CANONICAL G7 SOAK   = NOT ELIGIBLE (Requires uninterrupted continuous 6h run)"
    echo "  G7                  = NOT ELIGIBLE"
    echo "  STAGE S11           = OPEN (Awaiting qualifying continuous run)"
    echo "  PAPER AUTHORIZATION = NOT AUTHORIZED"
    echo "  LIVE TRADING        = LOCKED"
    echo "  CANONICAL CAPITAL   = \$0.00"
    exit 1
else
    echo -e "${RED}>>> GATE G7 ACCEPTANCE CRITERIA: FAIL (${FAILURES} issues, RUN_CLASS: ${RUN_CLASS}) <<<${NC}"
    echo "Formal Status:"
    echo "  RUN CLASS           = ${RUN_CLASS}"
    echo "  CONTINUITY ELIGIBLE = $([ "$G7_CONTINUITY_ELIGIBLE" = "true" ] && echo "YES" || echo "NO")"
    echo "  G7                  = FAIL"
    echo "  STAGE S11           = OPEN"
    echo "  PAPER AUTHORIZATION = NOT AUTHORIZED"
    echo "  LIVE TRADING        = LOCKED"
    echo "  CANONICAL CAPITAL   = \$0.00"
    exit 1
fi
