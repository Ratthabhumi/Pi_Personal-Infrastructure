import importlib.util
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('storage', ROOT / 'scripts/recovery/inspect_storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


class StorageSafety(unittest.TestCase):
    def test_non_root_never_executes_commands(self):
        with patch.object(storage.os, 'geteuid', return_value=1000, create=True), patch.object(storage, 'run') as run:
            result = storage.main('synthetic')
        self.assertEqual(result['classification'], 'ACCESS_BLOCKED')
        run.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'Linux mount protocol mocked; no actual root or mount')
    def test_metadata_scan_uses_no_replay_and_never_reads_or_deletes_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docker').mkdir()
            secret = root / 'docker/.env'
            secret.write_text('synthetic-private-marker')
            calls = []

            def run(args):
                calls.append(args)
                command = args[0]
                if command == 'vgs': return subprocess.CompletedProcess(args, 0, '{"report":[]}', '')
                if command == 'ufw': return subprocess.CompletedProcess(args, 0, 'Status: active', '')
                if command == '/usr/sbin/sshd': return subprocess.CompletedProcess(args, 0, 'pubkeyauthentication yes\npermitrootlogin no', '')
                if command == 'blkid': return subprocess.CompletedProcess(args, 0, '/dev/null' if '-U' in args else 'ext4', '')
                if command == 'blockdev': return subprocess.CompletedProcess(args, 0, '1000203091968', '')
                if command == 'findmnt': return subprocess.CompletedProcess(args, 1 if '--source' in args else 0, 'ro,noload,nodev,nosuid,noexec', '')
                if command in ['mount', 'umount']: return subprocess.CompletedProcess(args, 0, '', '')
                self.fail('Unexpected command: ' + command)

            with patch.object(storage.os, 'geteuid', return_value=0), patch.object(storage, 'run', side_effect=run), patch.object(storage.tempfile, 'mkdtemp', return_value=tmp):
                result = storage.main('11111111-1111-1111-1111-111111111111')
            self.assertEqual(result['classification'], 'EXISTING_DATA_RECOVERABLE')
            self.assertEqual(result['stage'], 'complete')
            self.assertEqual(secret.read_text(), 'synthetic-private-marker')
            mount = next(a for a in calls if a[0] == 'mount')
            self.assertEqual(mount[mount.index('-o') + 1], 'ro,noload,nodev,nosuid,noexec')
            self.assertTrue(any(a[0] == 'umount' for a in calls))
            self.assertNotIn('synthetic-private-marker', str(result))

    def test_unapproved_uuid_does_not_query_or_mount_disks(self):
        with patch.object(storage.os, 'geteuid', return_value=0, create=True), patch.object(storage, 'run') as run:
            result = storage.main('not-a-uuid')
        run.assert_not_called()
        self.assertEqual(result['stage'], 'identity')


class RestoreGate(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible CLI provided in Linux CI')
    def test_no_authority_and_acash_selection_stop_before_mount_or_deployment(self):
        cases = [None, {
            'homelab_restore_authorized': True,
            'homelab_storage_uuid': '11111111-1111-1111-1111-111111111111',
            'homelab_compose_sha256': 'a' * 64,
            'homelab_services': ['acash'],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / 'hosts'
            inventory.write_text('[home_servers]\nlocalhost ansible_connection=local\n')
            for variables in cases:
                args = ['ansible-playbook', '-i', str(inventory), str(ROOT / 'ansible/playbooks/01_deploy_homelab.yml')]
                if variables:
                    import json
                    args += ['--extra-vars', json.dumps(variables)]
                result = subprocess.run(args, text=True, capture_output=True, timeout=90, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Inspect data/secrets and approve exact UUID', result.stdout)
                self.assertNotIn('TASK [Read the actual data mount', result.stdout)


if __name__ == '__main__':
    unittest.main()
