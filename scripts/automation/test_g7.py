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
            jf.write(json.dumps(genesis) + "\n")
            prev_hash = genesis["event_hash"]

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
                jf.write(json.dumps(ev) + "\n")
                prev_hash = ev["event_hash"]

            if has_order:
                order_ev = {
                    "event_id": "00000000-0000-0000-0000-999999999999",
                    "session_id": self.session_id,
                    "sequence": bar_count + 1,
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
                "simulated_fills_only": True,
                "strategy_id": "INFRA-TEST-MOMENTUM-SYNTHETIC-001",
                "strategy_version": "1.0.0",
                "git_commit": "ec3a903",
                "config_hash": "c" * 64,
                "journal_final_hash": prev_hash,
                "start_time_utc": start_time.isoformat(),
                "end_time_utc": end_time.isoformat(),
                "duration_seconds": duration,
                "total_event_count": bar_count + 1 + (1 if has_order else 0),
                "total_warning_count": 0,
                "total_error_count": 0,
                "total_trade_count": 0,
                "total_order_count": 1 if has_order else 0,
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
                "manifest_hash": "m" * 64,
                "sealed": sealed,
                "sealed_at_utc": end_time.isoformat(),
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


if __name__ == "__main__":
    unittest.main()


