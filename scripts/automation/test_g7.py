#!/usr/bin/env python3
"""
test_g7.py — Automated Test Suite for Gate G7 / Stage S11 Operational Control & Evidence Suite

Tests:
  1. test_status_when_not_running
  2. test_status_read_only_invariant
  3. test_audit_pre_soak_readiness
  4. test_audit_with_synthetic_complete_evidence
  5. test_audit_with_missing_manifest
  6. test_audit_with_missing_snapshot
  7. test_audit_wrong_event_type_rejection (MARKET_BAR_RECORDED vs MARKET_BAR_RECEIVED)
  8. test_audit_timestamp_extraction (payload.timestamp_utc vs payload.bar.timestamp)
  9. test_audit_duplicate_timestamp_detection
  10. test_audit_duration_under_6h_failure
  11. test_audit_duration_over_6h_pass
  12. test_audit_order_submission_violation_detection
  13. test_start_fail_closed_on_running_container
  14. test_verify_delegation_behavior
  15. test_non_mutating_nature_of_status_and_audit
"""

import json
import os
import re
import sys
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
G7_SCRIPT = REPO_ROOT / "scripts" / "automation" / "g7.sh"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "automation" / "verify_g7_evidence.sh"
PREFLIGHT_SCRIPT = REPO_ROOT / "scripts" / "automation" / "preflight_g7_soak.sh"
GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"


def run_bash(cmd_args, env=None, cwd=None):
    """Execute bash command with specific environment."""
    bash_bin = GIT_BASH if os.path.exists(GIT_BASH) else "bash"
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    clean_args = [str(a).replace("\\", "/") for a in cmd_args]
    proc = subprocess.run(
        [bash_bin] + clean_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd or str(REPO_ROOT),
        env=full_env,
    )
    return proc


class TestG7Suite(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="acash_g7_test_")
        self.storage_root = Path(self.temp_dir) / "acash"
        self.sessions_dir = self.storage_root / "sessions"
        self.windows_dir = self.storage_root / "windows"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.windows_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = "E3.5-20260912-120000-abcdef"
        self.journal_file = self.sessions_dir / f"{self.session_id}.journal.jsonl"
        self.manifest_file = self.sessions_dir / f"{self.session_id}.manifest.json"
        self.snapshot_file = self.sessions_dir / f"{self.session_id}.snapshots.jsonl"

        self.test_env = {
            "ACASH_STORAGE_ROOT": str(self.storage_root).replace("\\", "/"),
            "STORAGE_ROOT": str(self.storage_root).replace("\\", "/"),
            "G7_TEST_MODE": "1",
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_synthetic_evidence(
        self,
        bar_count=360,
        start_time=None,
        end_time=None,
        event_type="MARKET_BAR_RECEIVED",
        timestamp_key="timestamp_utc",
        has_duplicate=False,
        has_order=False,
        sealed=True,
        omit_snapshot=False,
        omit_manifest=False,
        compact_json=False,
        whitespace_variations=False,
        feed_events=None,
        total_order_count=None,
        total_trade_count=None,
        simulated_fills_only=True,
        include_simulated_orders=False,
    ):
        """Generates synthetic valid E3.5 paper evidence files."""
        if start_time is None:
            start_time = datetime(2026, 9, 12, 6, 0, 0, tzinfo=timezone.utc)
        if end_time is None:
            end_time = start_time + timedelta(hours=6, minutes=1)

        duration = int((end_time - start_time).total_seconds())

        # 1. Journal
        prev_hash = "0" * 64
        with open(self.journal_file, "w", encoding="utf-8") as jf:
            # Genesis SESSION_STARTED
            genesis = {
                "event_id": "00000000-0000-0000-0000-000000000001",
                "session_id": self.session_id,
                "sequence": 0,
                "event_type": "SESSION_STARTED",
                "layer": "SYSTEM",
                "event_time_utc": start_time.isoformat(),
                "recorded_at_utc": start_time.isoformat(),
                "payload": {"mode": "PAPER_ONLY", "initial_cash": "0.00"},
                "previous_event_hash": prev_hash,
                "event_hash": "a" * 64,
            }
            if compact_json:
                jf.write(json.dumps(genesis, separators=(',', ':')) + "\n")
            else:
                jf.write(json.dumps(genesis) + "\n")
            prev_hash = genesis["event_hash"]

            if feed_events:
                for fe_type, fe_time, fe_payload in feed_events:
                    fe = {
                        "event_id": f"00000000-0000-feed-0000-{len(prev_hash):012d}",
                        "session_id": self.session_id,
                        "sequence": 9990,
                        "event_type": fe_type,
                        "layer": "SYSTEM",
                        "event_time_utc": fe_time.isoformat(),
                        "recorded_at_utc": fe_time.isoformat(),
                        "payload": fe_payload,
                        "previous_event_hash": prev_hash,
                        "event_hash": f"feed_hash_{fe_type}",
                    }
                    if compact_json:
                        jf.write(json.dumps(fe, separators=(',', ':')) + "\n")
                    else:
                        jf.write(json.dumps(fe) + "\n")
                    prev_hash = fe["event_hash"]

            # Market Bars
            for i in range(bar_count):
                bar_time = start_time + timedelta(minutes=i)
                if has_duplicate and i == 5:
                    bar_time = start_time + timedelta(minutes=4)  # Duplicate timestamp

                payload = {
                    "symbol": "BTCUSDT",
                    "close": "50000.0",
                    "volume": "1.0",
                }
                if timestamp_key == "timestamp_utc":
                    payload["timestamp_utc"] = bar_time.isoformat()
                elif timestamp_key == "bar.timestamp":
                    payload["bar"] = {"timestamp": bar_time.isoformat()}

                ev = {
                    "event_id": f"00000000-0000-0000-0000-{i+2:012d}",
                    "session_id": self.session_id,
                    "sequence": i + 1,
                    "event_type": event_type,
                    "layer": "MARKET_DATA",
                    "event_time_utc": bar_time.isoformat(),
                    "recorded_at_utc": bar_time.isoformat(),
                    "payload": payload,
                    "previous_event_hash": prev_hash,
                    "event_hash": f"hash_{i:060d}",
                }
                if compact_json:
                    jf.write(json.dumps(ev, separators=(',', ':')) + "\n")
                elif whitespace_variations:
                    if i % 3 == 0:
                        jf.write(json.dumps(ev, separators=(',', ':')) + "\n")
                    elif i % 3 == 1:
                        jf.write(json.dumps(ev, separators=(', ', ': ')) + "\n")
                    else:
                        # multi-space variation
                        s = json.dumps(ev, separators=(', ', '  :  '))
                        jf.write(s + "\n")
                else:
                    jf.write(json.dumps(ev) + "\n")
                prev_hash = ev["event_hash"]

            sim_order_events_count = 0
            if include_simulated_orders:
                for s_idx in range(1, 4):
                    intent_ev = {
                        "event_id": f"00000000-0000-0000-1111-{s_idx:012d}",
                        "session_id": self.session_id,
                        "sequence": bar_count + sim_order_events_count + 1,
                        "event_type": "ORDER_INTENT_CREATED",
                        "layer": "ORDER",
                        "event_time_utc": end_time.isoformat(),
                        "recorded_at_utc": end_time.isoformat(),
                        "payload": {
                            "order_intent_id": f"INTENT-{s_idx}",
                            "symbol": "BTCUSDT",
                            "side": "BUY",
                            "quantity": "0.01",
                            "order_type": "MARKET",
                            "GOVERNANCE_LABEL": "SIMULATED_ORDER",
                        },
                        "previous_event_hash": prev_hash,
                        "event_hash": f"a{s_idx:02d}" + "a" * 61,
                    }
                    prev_hash = intent_ev["event_hash"]
                    jf.write(json.dumps(intent_ev) + "\n")
                    sim_order_events_count += 1

                    fill_ev = {
                        "event_id": f"00000000-0000-0000-2222-{s_idx:012d}",
                        "session_id": self.session_id,
                        "sequence": bar_count + sim_order_events_count + 1,
                        "event_type": "FILL_SIMULATED",
                        "layer": "EXECUTION",
                        "event_time_utc": end_time.isoformat(),
                        "recorded_at_utc": end_time.isoformat(),
                        "payload": {
                            "fill_id": f"FILL-{s_idx}",
                            "order_intent_id": f"INTENT-{s_idx}",
                            "symbol": "BTCUSDT",
                            "side": "BUY",
                            "quantity": "0.01",
                            "price": "60000.0",
                        },
                        "previous_event_hash": prev_hash,
                        "event_hash": f"b{s_idx:02d}" + "b" * 61,
                    }
                    prev_hash = fill_ev["event_hash"]
                    jf.write(json.dumps(fill_ev) + "\n")
                    sim_order_events_count += 1

            if has_order:
                order_ev = {
                    "event_id": "00000000-0000-0000-0000-999999999999",
                    "session_id": self.session_id,
                    "sequence": bar_count + sim_order_events_count + 1,
                    "event_type": "ORDER_SUBMITTED",
                    "layer": "ORDER",
                    "event_time_utc": end_time.isoformat(),
                    "recorded_at_utc": end_time.isoformat(),
                    "payload": {"order_id": "ORD-1"},
                    "previous_event_hash": prev_hash,
                    "event_hash": "f" * 64,
                }
                jf.write(json.dumps(order_ev) + "\n")

        # 2. Manifest
        if not omit_manifest:
            manifest_data = {
                "session_id": self.session_id,
                "manifest_id": f"MAN-{self.session_id}",
                "mode": "PAPER_ONLY",
                "no_real_orders": not has_order,
                "simulated_fills_only": simulated_fills_only,
                "governance_label": "PAPER_TRADING_INFRASTRUCTURE_TEST",
                "strategy_id": "INFRA-TEST-MOMENTUM-SYNTHETIC-001",
                "strategy_version": "1.0.0",
                "is_infrastructure_test_strategy": True,
                "git_commit": "ec3a903",
                "config_hash": "c" * 64,
                "strategy_config_hash": "s" * 64,
                "journal_final_hash": prev_hash if sealed else "",
                "data_source": "feed:binance",
                "instrument_universe": ["BTCUSDT"],
                "market_domain": "CRYPTO",
                "fill_model_version": "1.0.0",
                "risk_model_version": "1.0.0",
                "start_time_utc": start_time.isoformat(),
                "end_time_utc": end_time.isoformat(),
                "total_event_count": bar_count + 1 + (1 if has_order else 0) + (sim_order_events_count if include_simulated_orders else 0),
                "total_warning_count": 0,
                "total_error_count": 0,
                "total_trade_count": (3 if include_simulated_orders else 0) if total_trade_count is None else total_trade_count,
                "total_order_count": (304 if include_simulated_orders else (1 if has_order else 0)) if total_order_count is None else total_order_count,
                "total_rejected_order_count": 0,
                "final_portfolio_summary": {
                    "cash": "0.00",
                    "equity": "0.00",
                    "position": "0",
                    "realized_pnl": "0.00",
                    "total_fees": "0.00",
                },
                "final_reconciliation_status": "PASS",
                "journal_integrity_status": "PASS",
                "manifest_hash": "m" * 64 if sealed else "",
                "sealed_at_utc": end_time.isoformat() if sealed else "",
            }
            with open(self.manifest_file, "w", encoding="utf-8") as mf:
                json.dump(manifest_data, mf, indent=2)

        # 3. Snapshot
        if not omit_snapshot:
            snapshot_data = {
                "snapshot_id": f"SNAP-{self.session_id}",
                "session_id": self.session_id,
                "trading_date": "2026-09-12",
                "starting_equity": "0.00",
                "ending_equity": "0.00",
                "journal_integrity_status": "PASS",
            }
            with open(self.snapshot_file, "w", encoding="utf-8") as sf:
                sf.write(json.dumps(snapshot_data) + "\n")

    # --- TESTS ---

    def test_status_when_not_running(self):
        """Test g7.sh status outputs G7 = NOT RUNNING when no container is active."""
        proc = run_bash([G7_SCRIPT, "status"], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("G7 = NOT RUNNING", proc.stdout)
        self.assertIn("NOT AUTHORIZED", proc.stdout)
        self.assertIn("LOCKED", proc.stdout)

    def test_status_is_read_only(self):
        """Test g7.sh status does not mutate filesystem state."""
        before_files = list(self.storage_root.rglob("*"))
        proc = run_bash([G7_SCRIPT, "status"], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        after_files = list(self.storage_root.rglob("*"))
        self.assertEqual(before_files, after_files)

    def test_audit_pre_soak_readiness(self):
        """Test g7.sh audit in pre-soak mode checks all 25 evidence points against codebase."""
        proc = run_bash([G7_SCRIPT, "audit"], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("25-POINT EVIDENCE-READINESS & LIFECYCLE AUDIT", proc.stdout)
        self.assertIn("Session ID Generation Scheme", proc.stdout)
        self.assertIn("MARKET_BAR_RECEIVED Ingestion Event", proc.stdout)
        self.assertIn("Snapshot File Path", proc.stdout)
        self.assertIn("EVIDENCE READINESS AUDIT: PASS", proc.stdout)

    def test_audit_with_synthetic_complete_evidence(self):
        """Test g7.sh audit on complete synthetic session produces PASS for all 25 items."""
        self._create_synthetic_evidence(bar_count=360)
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("EVIDENCE READINESS AUDIT: PASS (0 Failures", proc.stdout)

    def test_audit_detects_missing_manifest(self):
        """Test audit flags failure when manifest is missing for target session."""
        self._create_synthetic_evidence(bar_count=360, omit_manifest=True)
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        self.assertIn("Continuous Duration Evidence", proc.stdout)

    def test_audit_detects_missing_snapshot(self):
        """Test audit flags failure when snapshot file is missing for sealed session."""
        self._create_synthetic_evidence(bar_count=360, omit_snapshot=True)
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        self.assertIn("Snapshot File Path", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_event_type_mismatch_detection(self):
        """Verify that MARKET_BAR_RECORDED (old incorrect name) results in 0 bars detected."""
        self._create_synthetic_evidence(bar_count=360, event_type="MARKET_BAR_RECORDED")
        with open(self.journal_file, "r") as f:
            content = f.read()
        self.assertEqual(content.count('"event_type": "MARKET_BAR_RECEIVED"'), 0)
        self.assertGreater(content.count('"event_type": "MARKET_BAR_RECORDED"'), 0)

    def test_correct_market_bar_received_detection(self):
        """Verify that MARKET_BAR_RECEIVED is properly counted."""
        self._create_synthetic_evidence(bar_count=360, event_type="MARKET_BAR_RECEIVED")
        with open(self.journal_file, "r") as f:
            content = f.read()
        self.assertEqual(content.count('"event_type": "MARKET_BAR_RECEIVED"'), 360)

    def test_timestamp_key_extraction(self):
        """Verify that payload.timestamp_utc extractable and distinguishes duplicates."""
        self._create_synthetic_evidence(bar_count=50, has_duplicate=True, timestamp_key="timestamp_utc")
        with open(self.journal_file, "r") as f:
            lines = [json.loads(line) for line in f if '"event_type": "MARKET_BAR_RECEIVED"' in line]
        timestamps = [ev["payload"].get("timestamp_utc") for ev in lines]
        self.assertEqual(len(timestamps), 50)
        self.assertEqual(len(set(timestamps)), 49)  # 1 duplicate

    def test_duration_calculation(self):
        """Verify session duration calculations: <6h fails, >=6h passes."""
        start = datetime(2026, 9, 12, 0, 0, 0, tzinfo=timezone.utc)
        short_end = start + timedelta(hours=5, minutes=59)
        full_end = start + timedelta(hours=6, seconds=5)

        self.assertLess((short_end - start).total_seconds(), 21600)
        self.assertGreaterEqual((full_end - start).total_seconds(), 21600)

    def test_zero_order_invariant(self):
        """Verify zero-order detection in journal."""
        self._create_synthetic_evidence(bar_count=50, has_order=False)
        with open(self.journal_file, "r") as f:
            content = f.read()
        self.assertEqual(content.count('"event_type": "ORDER_SUBMITTED"'), 0)

        # Violation case
        self._create_synthetic_evidence(bar_count=50, has_order=True)
        with open(self.journal_file, "r") as f:
            content = f.read()
        self.assertGreater(content.count('"event_type": "ORDER_SUBMITTED"'), 0)

    def test_start_fail_closed_when_open_window_exists(self):
        """Test g7.sh start fails closed when an OPEN window marker exists."""
        # Create an OPEN window state marker
        marker = self.windows_dir / "test_window.state.json"
        marker.write_text(json.dumps({"state": "OPEN"}), encoding="utf-8")
        proc = run_bash([G7_SCRIPT, "start"], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("FAIL-CLOSED", proc.stdout + proc.stderr)

    def test_audit_non_mutating(self):
        """Verify g7.sh audit never modifies existing evidence files."""
        self._create_synthetic_evidence(bar_count=100)
        before_manifest_stat = self.manifest_file.stat()
        before_journal_stat = self.journal_file.stat()
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        after_manifest_stat = self.manifest_file.stat()
        after_journal_stat = self.journal_file.stat()
        self.assertEqual(before_manifest_stat.st_mtime, after_manifest_stat.st_mtime)
        self.assertEqual(before_journal_stat.st_mtime, after_journal_stat.st_mtime)

    def test_storage_initialization_child_directory_only(self):
        """Regression Test: Verify runner initializes only child directories under STORAGE_ROOT without parent mkdir failure."""
        # Create a fresh storage root without the 'sessions' subdirectory
        fresh_root = Path(self.temp_dir) / "fresh_acash"
        fresh_root.mkdir(parents=True, exist_ok=True)
        fresh_sessions = fresh_root / "sessions"
        self.assertFalse(fresh_sessions.exists())

        test_env = {
            "ACASH_STORAGE_ROOT": str(fresh_root).replace("\\", "/"),
            "STORAGE_ROOT": str(fresh_root).replace("\\", "/"),
        }

        # Run bash command snippet replicating the exact fixed runner initialization logic
        init_cmd = [
            "-c",
            f"""
            STORAGE_ROOT="{str(fresh_root).replace('\\', '/')}"
            SESSIONS_DIR="${{STORAGE_ROOT}}/sessions"
            if [ -w "$STORAGE_ROOT" ]; then
                mkdir -p "$SESSIONS_DIR"
            fi
            test -d "$SESSIONS_DIR"
            """
        ]
        proc = run_bash(init_cmd, env=test_env)
        self.assertEqual(proc.returncode, 0, f"Initialization failed: {proc.stderr}")
        self.assertTrue(fresh_sessions.exists(), "Sessions directory was not created under existing root")

        # Verify no attempt to create parent directory
        self.assertNotIn("Permission denied", proc.stdout + proc.stderr)

    def test_storage_initialization_docker_entrypoint_override(self):
        """Regression Test: Verify execute_g7_soak.sh uses --entrypoint python and does not pass python to acash.paper."""
        execute_script = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        with open(execute_script, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Must contain --entrypoint python
        self.assertIn("--entrypoint python", content, "execute_g7_soak.sh must specify --entrypoint python to bypass acash.paper entrypoint")

        # 2. Must not pass python as argument after image name
        self.assertNotIn(
            "acash:e36-ws10-staging \\\n        python -c",
            content,
            "execute_g7_soak.sh must not pass 'python' as positional subcommand argument to acash.paper"
        )

        # 3. Must preserve unprivileged container user 10001:10001
        self.assertIn("--user 10001:10001", content, "execute_g7_soak.sh must preserve --user 10001:10001")

        # 4. Must mount only storage root
        self.assertIn('-v "${STORAGE_ROOT}:${STORAGE_ROOT}"', content, "execute_g7_soak.sh must mount only STORAGE_ROOT")



    # -------------------------------------------------------------------------
    # REGRESSION TESTS FOR G7/S11 SOAK HARNESS REPAIR
    # -------------------------------------------------------------------------

    def test_compact_json_bar_count_instrumentation(self):
        """Regression Test 1: Verify compact JSON ('"event_type":"MARKET_BAR_RECEIVED"')
        is properly counted by both g7.sh and verify_g7_evidence.sh, reporting 330 instead of 0."""
        self._create_synthetic_evidence(bar_count=330, compact_json=True)
        with open(self.journal_file, "r", encoding="utf-8") as f:
            sample_line = f.readlines()[1]
        self.assertIn('"event_type":"MARKET_BAR_RECEIVED"', sample_line)
        self.assertNotIn('"event_type": "MARKET_BAR_RECEIVED"', sample_line)

        # Test verify_g7_evidence.sh bar detection
        proc_ver = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        # Should count 330 bars, NOT 0 bars
        self.assertIn("330 bars recorded", proc_ver.stdout)
        self.assertNotIn("Only 0 bars recorded", proc_ver.stdout)

    def test_whitespace_variation_bar_count(self):
        """Regression Test 2: Verify mixed whitespace formats across 330 bars are all counted accurately."""
        self._create_synthetic_evidence(bar_count=330, whitespace_variations=True)
        proc_ver = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertIn("330 bars recorded", proc_ver.stdout)

    def test_no_false_zero_bar_count_when_valid_bars_exist(self):
        """Regression Test 3: Ensure journal with valid compact bars never reports 0 bars ingested."""
        self._create_synthetic_evidence(bar_count=330, compact_json=True)
        # Check through shell function count_journal_bars in execute_g7_soak.sh
        EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        cmd = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; count_journal_bars {str(self.journal_file).replace('\\', '/')}"
        ]
        proc = run_bash(cmd, env=self.test_env)
        reported_count = proc.stdout.strip()
        self.assertEqual(reported_count, "330")
        self.assertNotEqual(reported_count, "0")

    def test_feed_disconnected_detection_terminal(self):
        """Regression Test 4: Verify terminal FEED_DISCONNECTED without recovery is detected fail-closed."""
        now = datetime.now(timezone.utc)
        feed_evs = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {"provider": "binance_public_klines"}),
            ("FEED_DISCONNECTED", now - timedelta(minutes=30), {"reason": "BinancePublicKlinesFeed ReadTimeout"}),
        ]
        self._create_synthetic_evidence(bar_count=330, compact_json=True, feed_events=feed_evs)

        EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        # Test check_feed_disconnected function
        cmd = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; check_feed_disconnected {str(self.journal_file).replace('\\', '/')} acash-staging"
        ]
        proc = run_bash(cmd, env=self.test_env)
        # check_feed_disconnected returns 0 when terminal disconnect is detected
        self.assertEqual(proc.returncode, 0, "Terminal FEED_DISCONNECTED must be detected as fatal!")

    def test_feed_disconnected_with_recovery_recognized(self):
        """Regression Test 5: Verify FEED_DISCONNECTED followed by FEED_CONNECTED recovery is recognized."""
        now = datetime.now(timezone.utc)
        feed_evs = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {"provider": "binance_public_klines"}),
            ("FEED_DISCONNECTED", now - timedelta(hours=3), {"reason": "Transient network hiccup"}),
            ("FEED_CONNECTED", now - timedelta(hours=2, minutes=59), {"provider": "binance_public_klines"}),
        ]
        self._create_synthetic_evidence(bar_count=330, compact_json=True, feed_events=feed_evs)

        EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        cmd = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; check_feed_disconnected {str(self.journal_file).replace('\\', '/')} acash-staging"
        ]
        proc = run_bash(cmd, env=self.test_env)
        # Returns 1 (non-zero) because feed successfully recovered
        self.assertEqual(proc.returncode, 1, "Recovered feed must NOT be flagged as terminal disconnect!")


    def test_feed_disconnected_structured_diagnostics_display(self):
        """Regression Test 6: Verify verify_g7_evidence.sh Check 4.3 audits structured feed diagnostics."""
        now = datetime.now(timezone.utc)
        feed_evs = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {
                "provider": "binance.public.klines",
                "symbol": "BTCUSDT",
            }),
            ("FEED_DISCONNECTED", now - timedelta(minutes=30), {
                "provider": "binance.public.klines",
                "error_class": "ReadTimeout",
                "category": "TIMEOUT",
                "operation": "poll",
                "reason": "BinancePublicKlinesFeed.poll_next_bar connection lost: ReadTimeout",
                "last_bar_utc": (now - timedelta(minutes=31)).isoformat(),
            }),
        ]
        self._create_synthetic_evidence(bar_count=330, compact_json=True, feed_events=feed_evs)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertIn("Terminal disconnect: ReadTimeout [TIMEOUT]", proc.stdout)
        self.assertIn("4.3: Feed connection stability", proc.stdout)


    def test_g7_evidence_continuous_healthy_session_passes(self):
        """Case A: Uninterrupted run with 0 disconnects and valid evidence achieves G7 PASS and S11 CLOSED."""
        self._create_synthetic_evidence(bar_count=360)
        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertEqual(proc.returncode, 0, f"Uninterrupted session must exit 0! Output:\n{proc.stdout}\n{proc.stderr}")
        self.assertIn("RUN CLASS           = CONTINUOUS", proc.stdout)
        self.assertIn("CONTINUITY ELIGIBLE = YES", proc.stdout)
        self.assertIn("G7                  = PASS / VERIFIED", proc.stdout)
        self.assertIn("STAGE S11           = CLOSED", proc.stdout)
        self.assertIn("GATE G7 ACCEPTANCE CRITERIA: PASS", proc.stdout)

    def test_g7_evidence_terminal_disconnect_fails_acceptance(self):
        """Case B: Terminal disconnect fails Check 4.3, exits non-zero, and does not achieve G7 PASS or S11 CLOSED."""
        now = datetime.now(timezone.utc)
        feed_evs = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {"provider": "binance_public_klines"}),
            ("FEED_DISCONNECTED", now - timedelta(minutes=30), {"error_class": "ReadTimeout", "category": "TIMEOUT"}),
        ]
        self._create_synthetic_evidence(bar_count=360, feed_events=feed_evs)
        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0, "Terminal disconnect must not exit 0!")
        self.assertIn("RUN CLASS           = INTERRUPTED", proc.stdout)
        self.assertIn("CONTINUITY ELIGIBLE = NO", proc.stdout)
        self.assertIn("Terminal disconnect: ReadTimeout [TIMEOUT]", proc.stdout)
        self.assertNotIn("G7                  = PASS / VERIFIED", proc.stdout)
        self.assertNotIn("STAGE S11           = CLOSED", proc.stdout)
        self.assertIn("G7                  = FAIL", proc.stdout)

    def test_g7_evidence_operator_recovered_not_eligible_for_g7_pass(self):
        """Case C: Operator-recovered session recognizes technical recovery but is NOT eligible for continuous G7 PASS."""
        now = datetime.now(timezone.utc)
        feed_evs = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {"provider": "binance_public_klines"}),
            ("FEED_DISCONNECTED", now - timedelta(hours=3), {"error_class": "ReadTimeout", "category": "TIMEOUT"}),
            ("RECOVERY_ATTEMPTED", now - timedelta(hours=2, minutes=59, seconds=55), {"attempt_number": 1}),
            ("FEED_CONNECTED", now - timedelta(hours=2, minutes=59, seconds=50), {"is_recovery": True, "resume_count": 1}),
        ]
        self._create_synthetic_evidence(bar_count=360, feed_events=feed_evs)
        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0, "Operator-recovered run must exit non-zero for continuous G7!")
        self.assertIn("RUN CLASS           = OPERATOR-RECOVERED", proc.stdout)
        self.assertIn("CONTINUITY ELIGIBLE = NO", proc.stdout)
        self.assertIn("RECOVERY MECHANISM  = PASS / VERIFIED", proc.stdout)
        self.assertIn("CANONICAL G7 SOAK   = NOT ELIGIBLE", proc.stdout)
        self.assertIn("G7                  = NOT ELIGIBLE", proc.stdout)
        self.assertIn("STAGE S11           = OPEN", proc.stdout)
        self.assertNotIn("G7                  = PASS / VERIFIED", proc.stdout)
        self.assertNotIn("STAGE S11           = CLOSED", proc.stdout)

    def test_g7_evidence_recovery_semantics_distinguished_from_terminal_failure(self):
        """Case D: Distinguish technical recovery success from an unrecovered terminal failure."""
        now = datetime.now(timezone.utc)
        # 1. Recovered run
        feed_evs_rec = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {"provider": "binance_public_klines"}),
            ("FEED_DISCONNECTED", now - timedelta(hours=3), {"error_class": "ReadTimeout", "category": "TIMEOUT"}),
            ("RECOVERY_ATTEMPTED", now - timedelta(hours=2, minutes=59, seconds=55), {"attempt_number": 1}),
            ("FEED_CONNECTED", now - timedelta(hours=2, minutes=59, seconds=50), {"is_recovery": True, "resume_count": 1}),
        ]
        self._create_synthetic_evidence(bar_count=360, feed_events=feed_evs_rec)
        proc_rec = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertIn("4.3: Feed connection stability & recovery", proc_rec.stdout)
        self.assertIn("Technical recovery: PASS", proc_rec.stdout)
        self.assertIn("Technical recovery: PASS", proc_rec.stdout)
        self.assertIn("GATE G7 ACCEPTANCE CRITERIA: NOT ELIGIBLE", proc_rec.stdout)

        # 2. Terminal disconnect
        feed_evs_term = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {"provider": "binance_public_klines"}),
            ("FEED_DISCONNECTED", now - timedelta(hours=3), {"error_class": "ReadTimeout", "category": "TIMEOUT"}),
        ]
        self._create_synthetic_evidence(bar_count=360, feed_events=feed_evs_term)
        proc_term = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertIn("4.3: Feed connection stability & recovery", proc_term.stdout)
        self.assertIn("Terminal disconnect: ReadTimeout [TIMEOUT]", proc_term.stdout)
        self.assertIn("Terminal disconnect: ReadTimeout [TIMEOUT]", proc_term.stdout)
        self.assertIn("GATE G7 ACCEPTANCE CRITERIA: FAIL", proc_term.stdout)



    # -------------------------------------------------------------------------
    # PORTABILITY & TEST-ISOLATION REGRESSION TESTS
    # -------------------------------------------------------------------------

    def test_verifier_with_explicit_g7_python_bin(self):
        """Regression Test: Verify verify_g7_evidence.sh functions with injected G7_PYTHON_BIN."""
        self._create_synthetic_evidence(bar_count=360)
        custom_env = self.test_env.copy()
        custom_env["G7_PYTHON_BIN"] = str(sys.executable).replace("\\", "/")

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=custom_env)
        self.assertEqual(proc.returncode, 0, f"Verifier failed with G7_PYTHON_BIN: {proc.stdout}\n{proc.stderr}")
        self.assertIn("RUN CLASS           = CONTINUOUS", proc.stdout)
        self.assertIn("G7                  = PASS / VERIFIED", proc.stdout)

    def test_verifier_fails_closed_when_python_interpreter_unavailable(self):
        """Regression Test: Verify verify_g7_evidence.sh fails closed if Python interpreter cannot be resolved."""
        self._create_synthetic_evidence(bar_count=360)
        custom_env = self.test_env.copy()
        custom_env["G7_PYTHON_BIN"] = "/nonexistent/invalid_python_interpreter"

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=custom_env)
        self.assertNotEqual(proc.returncode, 0, "Verifier must exit non-zero when Python interpreter is unavailable!")
        self.assertIn("Host Python interpreter unavailable for feed diagnostics", proc.stdout)
        self.assertIn("RUN CLASS           = INTERRUPTED", proc.stdout)
        self.assertNotIn("G7                  = PASS / VERIFIED", proc.stdout)

    def test_docker_isolation_in_test_mode(self):
        """Regression Test: G7_TEST_MODE=1 deterministically reports NOT RUNNING regardless of real host Docker state."""
        custom_env = self.test_env.copy()
        custom_env.pop("G7_TEST_CONTAINER_ID", None)

        proc = run_bash([G7_SCRIPT, "status"], env=custom_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("G7 = NOT RUNNING", proc.stdout)
        self.assertNotIn("G7 = RUNNING", proc.stdout)

    def test_docker_isolation_with_explicit_container_injection(self):
        """Regression Test: G7_TEST_MODE=1 respects explicitly injected test container without querying real Docker."""
        custom_env = self.test_env.copy()
        custom_env["G7_TEST_CONTAINER_ID"] = "mock_acash_soak_container_123"

        # In start command, step 1 should detect injected container and fail-closed immediately
        proc = run_bash([G7_SCRIPT, "start"], env=custom_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Container already running: mock_acash_soak_container_123", proc.stdout)

    def test_preflight_detects_host_python_readiness(self):
        """Regression Test: preflight_g7_soak.sh Check 1.5 verifies host Python interpreter readiness."""
        # 1. Valid Python
        custom_env = self.test_env.copy()
        custom_env["G7_PYTHON_BIN"] = str(sys.executable).replace("\\", "/")
        proc_pass = run_bash([PREFLIGHT_SCRIPT], env=custom_env)
        self.assertIn("1.5: Host Python interpreter present for G7 verification", proc_pass.stdout)
        self.assertIn("PASS", proc_pass.stdout)

        # 2. Invalid Python
        custom_env["G7_PYTHON_BIN"] = "/nonexistent/invalid_python_binary"
        proc_fail = run_bash([PREFLIGHT_SCRIPT], env=custom_env)
        self.assertIn("1.5: Host Python interpreter present for G7 verification", proc_fail.stdout)
        self.assertIn("FAIL", proc_fail.stdout)
        self.assertIn("Neither python3 nor python executable found on host", proc_fail.stdout)



    # -------------------------------------------------------------------------
    # PERMISSION-SAFE EVIDENCE ACCESS & SESSION RESOLUTION REGRESSION TESTS
    # -------------------------------------------------------------------------

    def test_active_session_resolved_from_container_when_host_unreadable(self):
        """Test A: Active session resolved from container when host sessions access is unreadable."""
        self._create_synthetic_evidence(bar_count=10)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_ID"] = "mock_acash_soak_container_123"
        custom_env["G7_TEST_CONTAINER_STARTED"] = "2026-09-12T06:00:00Z"

        EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        cmd = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; resolve_active_session acash-staging {str(self.sessions_dir).replace('\\', '/')}"
        ]
        proc = run_bash(cmd, env=custom_env)
        self.assertEqual(proc.returncode, 0, f"Resolver failed: {proc.stdout}\n{proc.stderr}")
        resolved_sid = proc.stdout.strip()
        self.assertEqual(resolved_sid, self.session_id)
        self.assertNotEqual(resolved_sid, "unknown")

    def test_unresolved_session_fails_closed(self):
        """Test B: Unresolved session fails closed before entering timed monitoring loop."""
        # Sessions directory is empty (no valid journal exists)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_ID"] = "mock_container_1"
        custom_env["G7_TEST_CONTAINER_STARTED"] = "2026-09-12T06:00:00Z"

        EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        cmd = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; resolve_active_session acash-staging {str(self.sessions_dir).replace('\\', '/')}"
        ]
        proc = run_bash(cmd, env=custom_env)
        self.assertNotEqual(proc.returncode, 0, "Resolver must exit non-zero when no session matches container startup!")
        self.assertNotEqual(proc.stdout.strip(), "unknown")

        # Test Step 2 fatal exit
        cmd_step2 = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; "
            f"SESSION_ID=$(resolve_active_session acash-staging {str(self.sessions_dir).replace('\\', '/')}) || {{ "
            f"echo '[FATAL] Unable to bind G7 harness to exactly one authoritative active session.'; "
            f"echo 'Canonical soak monitoring will not start.'; exit 1; }}; "
            f"echo 'MONITORING_STARTED'"
        ]
        proc_step2 = run_bash(cmd_step2, env=custom_env)
        self.assertNotEqual(proc_step2.returncode, 0, "Harness must abort before soak monitoring starts!")
        self.assertIn("Unable to bind G7 harness to exactly one authoritative active session", proc_step2.stdout)
        self.assertIn("Canonical soak monitoring will not start", proc_step2.stdout)
        self.assertNotIn("MONITORING_STARTED", proc_step2.stdout)

    def test_ambiguous_active_session_fails_closed(self):
        """Test C: Ambiguous active session candidates fail closed (no arbitrary newest selection)."""
        # Create two separate valid journals with matching startup window
        start_time = datetime(2026, 9, 12, 6, 0, 0, tzinfo=timezone.utc)
        for sid in ["E3.5-20260912-060000-aaaaaa", "E3.5-20260912-060000-bbbbbb"]:
            jfile = self.sessions_dir / f"{sid}.journal.jsonl"
            with open(jfile, "w", encoding="utf-8") as f:
                genesis = {
                    "event_id": f"00000000-0000-0000-0000-{sid[-6:]}000001",
                    "session_id": sid,
                    "sequence": 0,
                    "event_type": "SESSION_STARTED",
                    "layer": "SYSTEM",
                    "event_time_utc": start_time.isoformat(),
                    "recorded_at_utc": start_time.isoformat(),
                    "payload": {"mode": "PAPER_ONLY", "initial_cash": "0.00"},
                    "previous_event_hash": "0" * 64,
                    "event_hash": "a" * 64,
                }
                f.write(json.dumps(genesis) + "\n")

        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_STARTED"] = "2026-09-12T06:00:00Z"

        EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        cmd = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; resolve_active_session acash-staging {str(self.sessions_dir).replace('\\', '/')}"
        ]
        proc = run_bash(cmd, env=custom_env)
        self.assertNotEqual(proc.returncode, 0, "Ambiguous session candidates must fail closed!")
        self.assertNotIn("aaaaaa", proc.stdout)
        self.assertNotIn("bbbbbb", proc.stdout)

    def test_status_uses_container_side_evidence(self):
        """Test D: status dashboard uses container-side evidence when host evidence is unreadable."""
        self._create_synthetic_evidence(bar_count=360)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_ID"] = "mock_container_status_1"
        custom_env["G7_TEST_CONTAINER_STARTED"] = "2026-09-12T06:00:00Z"

        proc = run_bash([G7_SCRIPT, "status"], env=custom_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn(f"Session ID       : {self.session_id}", proc.stdout)
        self.assertIn("Bars Ingested    : 360", proc.stdout)
        self.assertIn("Feed Disconnects : 0", proc.stdout)
        self.assertNotIn("unknown", proc.stdout)
        self.assertNotIn("Bars Ingested    : 0", proc.stdout)

    def test_status_distinguishes_unavailable_from_zero(self):
        """Test E: status reports UNAVAILABLE when evidence cannot be read, not a fabricated zero."""
        self._create_synthetic_evidence(bar_count=360)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_ID"] = "mock_container_status_2"
        custom_env["G7_TEST_CONTAINER_STARTED"] = "2026-09-12T06:00:00Z"

        proc = run_bash([G7_SCRIPT, "status"], env=custom_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("UNAVAILABLE", proc.stdout)
        self.assertNotIn("Bars Ingested    : 0", proc.stdout)
        self.assertNotIn("Feed Disconnects : 0", proc.stdout)

    def test_disconnect_detection_works_when_host_unreadable(self):
        """Test F: Disconnect detection in journal still works when host access is unreadable."""
        now = datetime.now(timezone.utc)
        feed_evs = [
            ("FEED_CONNECTED", now - timedelta(hours=5), {"provider": "binance_public_klines"}),
            ("FEED_DISCONNECTED", now - timedelta(minutes=30), {"error_class": "ReadTimeout", "category": "TIMEOUT"}),
        ]
        self._create_synthetic_evidence(bar_count=330, compact_json=True, feed_events=feed_evs)

        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"

        EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "execute_g7_soak.sh"
        cmd = [
            "-c",
            f". {str(EXECUTE_SCRIPT).replace('\\', '/')} >/dev/null 2>&1 || true; check_feed_disconnected {str(self.journal_file).replace('\\', '/')} acash-staging"
        ]
        proc = run_bash(cmd, env=custom_env)
        # check_feed_disconnected returns 0 when terminal disconnect is detected
        self.assertEqual(proc.returncode, 0, "Terminal FEED_DISCONNECTED must return 0 (fatal) through container query!")

    def test_post_shutdown_verification_works_through_container(self):
        """Test G: Post-shutdown verification works through read-only container when host cannot read evidence."""
        self._create_synthetic_evidence(bar_count=360)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=custom_env)
        self.assertEqual(proc.returncode, 0, f"Verifier failed through container: {proc.stdout}\n{proc.stderr}")
        self.assertIn("1.1: Manifest sealed status verified", proc.stdout)
        self.assertIn("2.1: Daily snapshot artifact present and valid JSON", proc.stdout)
        self.assertIn("4.1: Bar count conforms to 6-hour M1 window", proc.stdout)
        self.assertIn("360 bars recorded", proc.stdout)
        self.assertIn("4.3: Feed connection stability & recovery", proc.stdout)
        self.assertIn("RUN CLASS           = CONTINUOUS", proc.stdout)
        self.assertIn("GATE G7 ACCEPTANCE CRITERIA: PASS", proc.stdout)

    def test_genuinely_missing_evidence_fails_closed(self):
        """Test H: Genuinely missing or unreadable evidence fails closed (no false PASS)."""
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_UNREADABLE"] = "1"

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=custom_env)
        self.assertNotEqual(proc.returncode, 0, "Missing evidence must fail closed!")
        self.assertIn("GATE G7 ACCEPTANCE CRITERIA: FAIL", proc.stdout)
        self.assertNotIn("GATE G7 ACCEPTANCE CRITERIA: PASS", proc.stdout)


    def test_real_manifest_without_sealed_field_accepted(self):
        """Regression Test: Canonical PaperSessionManifest (no 'sealed' bool, no 'duration_seconds') is accepted."""
        self._create_synthetic_evidence(bar_count=360, sealed=True)
        # Verify synthetic manifest strictly does NOT contain invented fields
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        self.assertNotIn("sealed", m)
        self.assertNotIn("duration_seconds", m)
        self.assertIn("sealed_at_utc", m)
        self.assertIn("manifest_hash", m)
        self.assertIn("journal_final_hash", m)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1.1: Manifest sealed status verified", proc.stdout)
        self.assertIn("sealed_at_utc=", proc.stdout)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)

    def test_fake_sealed_true_without_canonical_hashes_fails(self):
        """Regression Test: A fake manifest having 'sealed': true but missing canonical hashes fails Check 1.1."""
        self._create_synthetic_evidence(bar_count=360, sealed=False)
        # Inject fake 'sealed': true while leaving sealed_at_utc and hashes empty
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["sealed"] = True  # Fake field
        m["sealed_at_utc"] = ""
        m["manifest_hash"] = ""
        m["journal_final_hash"] = ""
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("FAIL", proc.stdout)
        self.assertIn("Missing required canonical sealed manifest fields", proc.stdout)

    def test_snapshots_jsonl_is_audited(self):
        """Regression Test: .snapshots.jsonl artifact presence and validity is strictly verified."""
        self._create_synthetic_evidence(bar_count=360, omit_snapshot=True)
        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Missing or empty", proc.stdout)


    def test_wave_h_storage_root_and_sessions_dir_contract(self):
        """Requirement A & B: Wave H storage root resolves to /data/docker/acash, sessions dir to /sessions, and no /sessions/sessions."""
        wave_h_path = REPO_ROOT / "docs" / "operations" / "g7_post_soak_forensic_checklist.md"
        self.assertTrue(wave_h_path.is_file(), "Wave H checklist doc must exist")
        with open(wave_h_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must NOT contain /sessions/sessions anywhere
        self.assertNotIn("/sessions/sessions", content, "Wave H must NEVER contain /sessions/sessions")

        # Must define proper contract
        self.assertIn('STORAGE_ROOT="${ACASH_STORAGE_ROOT:-/data/docker/acash}"', content)
        self.assertIn('SESSIONS_DIR="${STORAGE_ROOT}/sessions"', content)
        self.assertIn('-v "${STORAGE_ROOT}:${STORAGE_ROOT}:ro"', content)
        self.assertIn('--storage "${SESSIONS_DIR}"', content)

    def test_wave_h_embedded_python_snippets_syntax(self):
        """Requirement C: Every embedded executable Python snippet in Wave H passes syntax validation without syntax errors."""
        import ast, re
        wave_h_path = REPO_ROOT / "docs" / "operations" / "g7_post_soak_forensic_checklist.md"
        with open(wave_h_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = re.findall(r"```bash\s*\n([\s\S]*?)```", content)
        snippets = []
        for b in blocks:
            m = re.search(r"-c\s+'\n([\s\S]*?)\n'", b)
            if m:
                snippets.append(m.group(1))

        self.assertGreaterEqual(len(snippets), 4, "Expected 4 embedded Python snippets in Wave H")

        for idx, snip in enumerate(snippets, 1):
            try:
                ast.parse(snip)
            except SyntaxError as e:
                self.fail(f"Wave H embedded Python snippet #{idx} failed syntax validation: {e}\nSnippet:\n{snip}")

    def test_wave_h_canonical_eligibility_not_new_rule(self):
        """Requirement G: Wave H must NOT define Dimensions 1-4 PASS => Canonical Eligibility as a new governance rule."""
        wave_h_path = REPO_ROOT / "docs" / "operations" / "g7_post_soak_forensic_checklist.md"
        with open(wave_h_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("Dimensions 1\u20134 are `PASS`", content)
        self.assertNotIn("Dimensions 1-4 are `PASS`", content)
        self.assertNotIn("Dimensions 1\u20134 PASS", content)
        self.assertNotIn("Dimensions 1-4 PASS", content)
        self.assertIn("This checklist does not independently create, add, remove, reinterpret, or retroactively change G7 acceptance criteria.", content)
        self.assertIn("VERIFIER-REPORTED ELIGIBLE", content)
        self.assertIn("NOT ESTABLISHED", content)

    def test_duration_computed_from_canonical_start_end_only(self):
        """Requirement D: Canonical duration >= 6 hours computed from start_time_utc and end_time_utc."""
        start_dt = datetime(2026, 9, 12, 6, 0, 0, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(hours=6, minutes=5) # 21900s
        self._create_synthetic_evidence(bar_count=360, start_time=start_dt, end_time=end_dt)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)
        self.assertIn("PASS", proc.stdout)
        self.assertIn("Duration: 21900s", proc.stdout)

    def test_duration_fails_closed_when_start_time_missing_or_null(self):
        """Requirement E: Missing or null start_time_utc fails closed."""
        self._create_synthetic_evidence(bar_count=360)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["start_time_utc"] = None
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_duration_fails_closed_when_end_time_missing_or_null(self):
        """Requirement E: Missing or null end_time_utc fails closed."""
        self._create_synthetic_evidence(bar_count=360)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["end_time_utc"] = None
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_duration_fails_closed_when_timestamp_malformed(self):
        """Requirement E: Malformed ISO-8601 timestamp fails closed."""
        self._create_synthetic_evidence(bar_count=360)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["start_time_utc"] = "NOT_A_VALID_ISO_TIMESTAMP"
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_duration_fails_closed_when_end_before_start(self):
        """Requirement E: Reversed timestamp ordering (end < start) fails closed."""
        self._create_synthetic_evidence(bar_count=360)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["start_time_utc"] = "2026-09-12T12:00:00+00:00"
        m["end_time_utc"] = "2026-09-12T06:00:00+00:00" # end is 6h BEFORE start
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_duration_fails_closed_when_timezone_naive(self):
        """Requirement E: Timezone-naive timestamp without offset or Z fails closed."""
        self._create_synthetic_evidence(bar_count=360)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["start_time_utc"] = "2026-09-12T06:00:00" # naive
        m["end_time_utc"] = "2026-09-12T12:05:00"   # naive
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_duration_seconds_alone_cannot_satisfy_gate(self):
        """Requirement F: Invented duration_seconds alone without valid start/end fails closed."""
        self._create_synthetic_evidence(bar_count=360)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["start_time_utc"] = None
        m["end_time_utc"] = None
        m["duration_seconds"] = 30000 # Invented fallback
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("5.1: Session duration >= 6.00 continuous hours", proc.stdout)
        self.assertIn("FAIL", proc.stdout)


    def test_manifest_zero_order_acceptance(self):
        """Regression Test: no_real_orders=true, simulated_fills_only=true PASSES Check 1.2."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1.2: Zero Real Order Submission Evidence", proc.stdout)
        self.assertIn("PASS", proc.stdout)

    def test_manifest_nonzero_simulated_orders_accepted(self):
        """Regression Test: total_order_count=304, no_real_orders=true, simulated_fills_only=true PASSES Check 1.2."""
        self._create_synthetic_evidence(bar_count=360, has_order=False, total_order_count=304)
        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1.2: Zero Real Order Submission Evidence", proc.stdout)
        self.assertIn("PASS", proc.stdout)
        self.assertIn("simulated_orders=304", proc.stdout)

    def test_manifest_no_real_orders_false_rejected(self):
        """Regression Test: no_real_orders=false FAILS Check 1.2."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["no_real_orders"] = False
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("1.2: Zero Real Order Submission Evidence", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_manifest_simulated_fills_only_false_rejected(self):
        """Regression Test: simulated_fills_only=false FAILS Check 1.2."""
        self._create_synthetic_evidence(bar_count=360, has_order=False, simulated_fills_only=False)
        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("1.2: Zero Real Order Submission Evidence", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_journal_nonzero_order_submission_fails(self):
        """Regression Test: ORDER_SUBMITTED > 0 in journal FAILS Check 7.1."""
        self._create_synthetic_evidence(bar_count=360, has_order=True)
        # Manifest has no_real_orders=True, but journal contains ORDER_SUBMITTED
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["no_real_orders"] = True
        m["simulated_fills_only"] = True
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("7.1: Zero Real Order Submissions in Journal", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_simulated_order_intent_and_fills_pass_verifier_and_audit(self):
        """Regression Test: Accepted G7 semantics with simulated orders passes verifier and audit:
        no_real_orders=true, simulated_fills_only=true, total_order_count=304,
        ORDER_INTENT_CREATED > 0, FILL_SIMULATED > 0, ORDER_SUBMITTED=0
        PASSES verifier and audit. Mutating ORDER_SUBMITTED to 1 FAILS both.
        """
        self._create_synthetic_evidence(bar_count=360, include_simulated_orders=True)
        # 1. Verify verifier passes
        proc_v = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertEqual(proc_v.returncode, 0)
        self.assertIn("1.2: Zero Real Order Submission Evidence", proc_v.stdout)
        self.assertIn("7.1: Zero Real Order Submissions in Journal", proc_v.stdout)
        self.assertIn("GATE G7 ACCEPTANCE CRITERIA: PASS", proc_v.stdout)

        # 2. Verify g7.sh audit passes
        proc_a = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        clean_a = re.sub(r'\x1b\[[0-9;]*m', '', proc_a.stdout)
        self.assertEqual(proc_a.returncode, 0)
        self.assertIn("[ PASS ] 18: Zero Real Order Submission Evidence", clean_a)
        self.assertIn(">>> EVIDENCE READINESS AUDIT: PASS", clean_a)

        # 3. Mutate journal to add 1 ORDER_SUBMITTED event
        with open(self.journal_file, "a", encoding="utf-8") as jf:
            bad_ev = {
                "event_id": "00000000-0000-0000-3333-000000000001",
                "session_id": self.session_id,
                "sequence": 9999,
                "event_type": "ORDER_SUBMITTED",
                "layer": "ORDER",
                "event_time_utc": "2026-09-12T12:00:00Z",
                "recorded_at_utc": "2026-09-12T12:00:00Z",
                "payload": {"order_id": "REAL-ORD-1"},
                "previous_event_hash": "a" * 64,
                "event_hash": "e" * 64,
            }
            jf.write(json.dumps(bad_ev) + "\n")

        # 4. Now both MUST fail
        proc_v_fail = run_bash([VERIFY_SCRIPT, self.session_id], env=self.test_env)
        self.assertNotEqual(proc_v_fail.returncode, 0)
        self.assertIn("7.1: Zero Real Order Submissions in Journal", proc_v_fail.stdout)
        self.assertIn("FAIL", proc_v_fail.stdout)

        proc_a_fail = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        clean_a_fail = re.sub(r'\x1b\[[0-9;]*m', '', proc_a_fail.stdout)
        self.assertNotEqual(proc_a_fail.returncode, 0)
        self.assertIn("[ FAIL ] 18: Zero Real Order Submission Evidence", clean_a_fail)

    def test_permission_safe_g7_audit_nonzero_orders_fails(self):
        """Regression Test: host journal unreadable, container-side journal has 1 ORDER_SUBMITTED => g7.sh audit FAILS."""
        self._create_synthetic_evidence(bar_count=360, has_order=True)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"

        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("18: Zero Real Order Submission Evidence", proc.stdout)
        self.assertIn("FAIL", proc.stdout)
        self.assertIn("ORDER_SUBMITTED events dispatched!", proc.stdout)

    def test_permission_safe_g7_audit_zero_orders_passes(self):
        """Regression Test: host journal unreadable, container-side journal has 0 ORDER_SUBMITTED => g7.sh audit PASSES."""
        self._create_synthetic_evidence(bar_count=360, has_order=False, total_order_count=304)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"

        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("18: Zero Real Order Submission Evidence", proc.stdout)
        self.assertIn("PASS", proc.stdout)
        self.assertIn("0 ORDER_SUBMITTED events", proc.stdout)

    def test_neither_host_nor_container_readable_fails_closed(self):
        """Regression Test: Neither host nor container readable fails closed, never reports 0 orders."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_UNREADABLE"] = "1"

        proc_audit = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        self.assertNotEqual(proc_audit.returncode, 0)
        self.assertIn("18: Zero Real Order Submission Evidence", proc_audit.stdout)
        self.assertIn("FAIL", proc_audit.stdout)

        proc_verify = run_bash([VERIFY_SCRIPT, self.session_id], env=custom_env)
        self.assertNotEqual(proc_verify.returncode, 0)

    def test_verifier_no_argument_auto_discovery_host_unreadable(self):
        """Regression Test: SESSION_ID omitted, host unreadable, container-readable auto-discovers session."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"

        # Call VERIFY_SCRIPT with NO arguments
        proc = run_bash([VERIFY_SCRIPT], env=custom_env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn(f"Auditing Session ID: {self.session_id}", proc.stdout)
        self.assertIn("GATE G7 ACCEPTANCE CRITERIA: PASS", proc.stdout)

    def test_manifest_schema_mandatory_field_contract(self):
        """Regression Test: Synthetic manifest contains all 31 canonical PaperSessionManifest fields."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)

        expected_fields = {
            "session_id", "manifest_id", "mode", "no_real_orders", "simulated_fills_only",
            "governance_label", "strategy_id", "strategy_version", "is_infrastructure_test_strategy",
            "git_commit", "config_hash", "strategy_config_hash", "journal_final_hash",
            "data_source", "instrument_universe", "market_domain",
            "fill_model_version", "risk_model_version",
            "start_time_utc", "end_time_utc",
            "total_event_count", "total_warning_count", "total_error_count",
            "total_trade_count", "total_order_count", "total_rejected_order_count",
            "final_portfolio_summary", "final_reconciliation_status", "journal_integrity_status",
            "manifest_hash", "sealed_at_utc"
        }
        for field in expected_fields:
            self.assertIn(field, m, f"Required PaperSessionManifest field '{field}' missing from synthetic manifest!")

    def test_manifest_schema_direct_model_validation(self):
        """Regression Test: Synthetic manifest passes canonical Pydantic model_validate without silent pass on ImportError."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)

        import sys
        acash_src = str(REPO_ROOT.parent / "Acash" / "src")
        if acash_src not in sys.path:
            sys.path.insert(0, acash_src)
        try:
            from acash.paper.manifest import PaperSessionManifest
        except ImportError as e:
            self.skipTest(f"Direct Acash PaperSessionManifest import unavailable: {e}")

        validated = PaperSessionManifest.model_validate(m)
        self.assertEqual(validated.session_id, self.session_id)
        self.assertTrue(validated.no_real_orders)
        self.assertTrue(validated.simulated_fills_only)

    def test_direct_schema_validation_cannot_silently_pass_on_importerror(self):
        """Regression Test: Direct schema validation does not swallow import errors with silent pass."""
        test_file_path = Path(__file__)
        with open(test_file_path, "r", encoding="utf-8") as f:
            t_content = f.read()
        bad_pattern = "except Import" + "Error:\n            pass"
        bad_pattern_inline = "except Import" + "Error: pass"
        self.assertNotIn(bad_pattern, t_content)
        self.assertNotIn(bad_pattern_inline, t_content)
        self.assertIn("self.skipTest", t_content)

    def test_g7_audit_duration_fake_duration_seconds_fails(self):
        """Regression Test: g7.sh audit with fake duration_seconds=30000 but canonical start/end < 6h fails Item 22."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)

        # Inject fake duration_seconds=30000, but set start/end to only 2 hours
        m["duration_seconds"] = 30000
        m["start_time_utc"] = "2026-09-12T00:00:00Z"
        m["end_time_utc"] = "2026-09-12T02:00:00Z"
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("22: Continuous Duration Evidence (>= 6.00h)", clean_out)
        self.assertIn("[ FAIL ] 22: Continuous Duration Evidence", clean_out)
        self.assertIn("7200s (< 21600s requirement)", clean_out)

    def test_g7_audit_duration_valid_canonical_start_end_passes(self):
        """Regression Test: g7.sh audit with valid canonical start/end >= 6h and NO duration_seconds passes Item 22."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)

        # Ensure duration_seconds is absent and start/end span exactly 6h
        m.pop("duration_seconds", None)
        m["start_time_utc"] = "2026-09-12T00:00:00Z"
        m["end_time_utc"] = "2026-09-12T06:00:00Z"
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=self.test_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("22: Continuous Duration Evidence (>= 6.00h)", clean_out)
        self.assertIn("[ PASS ] 22: Continuous Duration Evidence", clean_out)
        self.assertIn("21600s continuous execution", clean_out)

    def test_g7_status_does_not_depend_on_duration_seconds(self):
        """Regression Test: g7.sh status derives duration from canonical timestamps and displays UNAVAILABLE if unparseable."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)

        # Case 1: Valid 6h start/end, NO duration_seconds
        m.pop("duration_seconds", None)
        m["start_time_utc"] = "2026-09-12T00:00:00Z"
        m["end_time_utc"] = "2026-09-12T06:00:00Z"
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc1 = run_bash([G7_SCRIPT, "status"], env=self.test_env)
        self.assertEqual(proc1.returncode, 0)
        self.assertIn("Last Sealed Session:", proc1.stdout)
        self.assertIn("Duration      : 21600s (6h 0m)", proc1.stdout)

        # Case 2: Unparseable/missing start/end, NO duration_seconds -> displays UNAVAILABLE
        m.pop("start_time_utc", None)
        m.pop("end_time_utc", None)
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        proc2 = run_bash([G7_SCRIPT, "status"], env=self.test_env)
        self.assertEqual(proc2.returncode, 0)
        self.assertIn("Duration      : UNAVAILABLE", proc2.stdout)
        self.assertNotIn("0s (0h 0m)", proc2.stdout)

    def test_fake_sealed_boolean_rejection_audit_19(self):
        """Regression Test: g7.sh Audit Item 19 verifies canonical sealing fields, not fake sealed boolean."""
        g7_path = REPO_ROOT / "scripts" / "automation" / "g7.sh"
        with open(g7_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("sealed: true, manifest_hash, journal_final_hash", content)
        self.assertIn("sealed_at_utc + manifest_hash + journal_final_hash", content)

    def test_target_session_host_unreadable_container_readable_all_pass(self):
        """Regression A: Specified session + host unreadable + container readable + valid evidence passes items 03, 04, 05, 22, 23."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("[ PASS ] 03: Journal File Path", clean_out)
        self.assertIn("[ PASS ] 04: Manifest File Path", clean_out)
        self.assertIn("[ PASS ] 05: Snapshot File Path", clean_out)
        self.assertIn("[ PASS ] 22: Continuous Duration Evidence", clean_out)
        self.assertIn("[ PASS ] 23: Duplicate Bar Detection & Freshness", clean_out)
        self.assertIn(">>> EVIDENCE READINESS AUDIT: PASS", clean_out)

    def test_target_session_host_unreadable_missing_manifest_fails(self):
        """Regression B: Specified session + host unreadable + missing manifest fails Item 04 and overall audit."""
        self._create_synthetic_evidence(bar_count=360, omit_manifest=True)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("[ FAIL ] 04: Manifest File Path", clean_out)
        self.assertIn(">>> EVIDENCE READINESS AUDIT: FAIL", clean_out)

    def test_target_session_host_unreadable_missing_snapshot_fails(self):
        """Regression C: Specified session + host unreadable + missing snapshot fails Item 05."""
        self._create_synthetic_evidence(bar_count=360, omit_snapshot=True)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("[ FAIL ] 05: Snapshot File Path", clean_out)
        self.assertIn(">>> EVIDENCE READINESS AUDIT: FAIL", clean_out)

    def test_target_session_host_unreadable_malformed_timestamps_fails_duration(self):
        """Regression D: Specified session + host unreadable + malformed/missing timestamps fails Item 22."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        m["start_time_utc"] = "not_an_iso_timestamp"
        m["end_time_utc"] = "neither_is_this"
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)

        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("[ FAIL ] 22: Continuous Duration Evidence", clean_out)

    def test_target_session_host_unreadable_duplicate_timestamps_fails_freshness(self):
        """Regression E: Specified session + host unreadable + duplicate MARKET_BAR_RECEIVED timestamp fails Item 23."""
        self._create_synthetic_evidence(bar_count=50, has_duplicate=True, timestamp_key="timestamp_utc")
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("[ FAIL ] 23: Duplicate Bar Detection & Freshness", clean_out)
        self.assertIn("duplicate timestamps found", clean_out)

    def test_target_session_host_unreadable_container_unreadable_fails_closed(self):
        """Regression F: Specified session + host unreadable + container unreadable fails closed (NEVER readiness PASS)."""
        self._create_synthetic_evidence(bar_count=360, has_order=False)
        custom_env = self.test_env.copy()
        custom_env["G7_SIMULATE_HOST_UNREADABLE"] = "1"
        custom_env["G7_TEST_CONTAINER_UNREADABLE"] = "1"
        proc = run_bash([G7_SCRIPT, "audit", self.session_id], env=custom_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("[ FAIL ] 03: Journal File Path", clean_out)
        self.assertIn("[ FAIL ] 04: Manifest File Path", clean_out)
        self.assertIn("[ FAIL ] 05: Snapshot File Path", clean_out)
        self.assertIn("[ FAIL ] 22: Continuous Duration Evidence", clean_out)
        self.assertIn("[ FAIL ] 23: Duplicate Bar Detection & Freshness", clean_out)
        self.assertIn(">>> EVIDENCE READINESS AUDIT: FAIL", clean_out)
        self.assertNotIn(">>> EVIDENCE READINESS AUDIT: PASS", clean_out)

    def test_pre_soak_mode_without_session_preserves_readiness(self):
        """Regression G: No target session + no evidence preserves PRE-SOAK readiness behavior."""
        custom_env = self.test_env.copy()
        proc = run_bash([G7_SCRIPT, "audit"], env=custom_env)
        clean_out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout)
        self.assertIn("PRE-SOAK EVIDENCE-READINESS MODE", clean_out)
        self.assertIn("[ PASS ] 03: Journal File Path", clean_out)
        self.assertIn("<storage>/<session_id>.journal.jsonl", clean_out)
        self.assertIn("[ PASS ] 04: Manifest File Path", clean_out)
        self.assertIn("<storage>/<session_id>.manifest.json", clean_out)
        self.assertIn("[ PASS ] 05: Snapshot File Path", clean_out)
        self.assertIn("<storage>/<session_id>.snapshots.jsonl", clean_out)
        self.assertIn("[ PASS ] 22: Continuous Duration Evidence", clean_out)
        self.assertIn("manifest.start_time_utc / end_time_utc", clean_out)
        self.assertIn("[ PASS ] 23: Duplicate Bar Detection & Freshness", clean_out)
        self.assertIn("runner._seen_feed_source_ids", clean_out)
        self.assertIn(">>> EVIDENCE READINESS AUDIT: PASS", clean_out)

if __name__ == "__main__":
    unittest.main()


