"""Owner runs with sudo. Mounts only approved ext4 HDD read-only/no journal replay.

Never formats, replays journal, repairs fs, changes ownership/fstab or installs tools.
Only allowlisted directory-presence booleans leave the host; no private file reads.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


def run(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)


def require(args):
    p = run(args)
    if p.returncode:
        raise RuntimeError('COMMAND_FAILED')
    return p.stdout.strip()


def main(expected_uuid):
    report = {'observedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'classification': 'EXISTING_DATA_UNVERIFIED', 'stage': 'identity',
              'filesystemWritesRequested': False, 'packageOrServiceChanges': False,
              'cleanup': 'NOT_MOUNTED', 'checks': {}}
    mountpoint = None
    mounted = False
    try:
        if os.geteuid() != 0:
            raise PermissionError('OWNER_SUDO_REQUIRED')
        if not re.fullmatch(r'[a-fA-F0-9-]{36}', expected_uuid):
            raise ValueError('INVALID_UUID')
        lvm = run(['vgs', '--reportformat', 'json', '--units', 'b', '--nosuffix', '-o', 'vg_size,vg_free'])
        if lvm.returncode == 0:
            report['checks']['lvmCapacityOnly'] = json.loads(lvm.stdout).get('report', [])
        report['checks']['ufwActive'] = run(['ufw', 'status']).stdout.startswith('Status: active')
        ssh = run(['/usr/sbin/sshd', '-T'])
        if ssh.returncode == 0:
            allowed = {'pubkeyauthentication', 'passwordauthentication', 'permitrootlogin'}
            report['checks']['sshEffectiveAuthentication'] = {
                line.split()[0]: line.split()[1] for line in ssh.stdout.splitlines()
                if len(line.split()) == 2 and line.split()[0] in allowed}
        report['stage'] = 'resolve-approved-filesystem'
        device = Path(require(['blkid', '-U', expected_uuid])).resolve(strict=True)
        if not str(device).startswith('/dev/'):
            raise ValueError('NOT_A_BLOCK_DEVICE_PATH')
        if require(['blkid', '-s', 'TYPE', '-o', 'value', str(device)]) != 'ext4':
            raise ValueError('NOT_EXT4')
        size = int(require(['blockdev', '--getsize64', str(device)]))
        if not 900_000_000_000 <= size <= 1_100_000_000_000:
            raise ValueError('NOT_EXPECTED_1TB_FILESYSTEM')
        report['checks']['expectedFilesystemIdentityAndSize'] = 'PASS'
        # No remount or inspection of a filesystem already used by another operation.
        code = run(['findmnt', '--source', str(device), '--noheadings']).returncode
        if code != 1:
            raise RuntimeError('ALREADY_MOUNTED_OR_MOUNT_QUERY_FAILED')
        report['stage'] = 'read-only-no-replay-mount'
        mountpoint = Path(tempfile.mkdtemp(prefix='homelab-inspect-', dir='/run'))
        # A failed/timed-out mount can still have changed kernel mount state.
        # Always attempt ordinary cleanup of our unique mountpoint after requesting it.
        mounted = True
        report['cleanup'] = 'PENDING'
        require(['mount', '-t', 'ext4', '-o', 'ro,noload,nodev,nosuid,noexec', str(device), str(mountpoint)])
        options = require(['findmnt', '--mountpoint', str(mountpoint), '--noheadings', '--output', 'OPTIONS']).split(',')
        if not {'ro', 'nodev', 'nosuid', 'noexec'}.issubset(options) or not ({'noload', 'norecovery'} & set(options)):
            raise RuntimeError('MOUNT_OPTIONS_NOT_VERIFIED')
        report['checks']['readOnlyNoJournalReplay'] = 'PASS'
        report['stage'] = 'metadata-only-inspection'
        entries = list(mountpoint.iterdir())
        meaningful = [p for p in entries if p.name != 'lost+found']
        lost = mountpoint / 'lost+found'
        if lost.is_symlink():
            meaningful.append(lost)
        orphaned = not lost.is_symlink() and lost.is_dir() and any(lost.iterdir())
        report['checks']['topLevelEntryCountExcludingLostFound'] = len(meaningful)
        report['checks']['lostFoundNonempty'] = bool(orphaned)
        # Do not follow old symlinks into live host paths or read private contents.
        def present(relative):
            p = mountpoint
            for part in relative.split('/'):
                p = p / part
                if p.is_symlink():
                    return 'SYMLINK_NOT_FOLLOWED'
            return p.exists()
        report['checks']['knownLayout'] = {p: present(p) for p in [
            'docker', 'data/docker', 'backups', 'docker/postgres/data',
            'docker/nextcloud/data', 'docker/vaultwarden/data', 'docker/grafana/data', 'docker/.env']}
        report['classification'] = 'EXISTING_DATA_RECOVERABLE' if meaningful or orphaned else 'EMPTY_FILESYSTEM_CONFIRMED'
        report['limitation'] = 'Metadata readable only; no application consistency, file-content recovery or backup validity claim'
        report['stage'] = 'complete'
    except PermissionError:
        report['classification'] = 'ACCESS_BLOCKED'
        report['errorCode'] = 'PERMISSION_REQUIRED'
    except Exception as exc:
        report['errorCode'] = type(exc).__name__  # Never export messages or paths.
    finally:
        if mounted:
            try:
                if run(['umount', str(mountpoint)]).returncode == 0:
                    mounted = False
                    report['cleanup'] = 'UNMOUNTED'
                else:
                    report['cleanup'] = 'UNMOUNT_FAILED_OWNER_REQUIRED'
            except Exception:
                report['cleanup'] = 'UNMOUNT_FAILED_OWNER_REQUIRED'
        if mountpoint and not mounted:
            try:
                mountpoint.rmdir()  # Only the newly created empty mountpoint, never recursive.
            except OSError:
                report['cleanup'] = 'EMPTY_MOUNTPOINT_RETAINED'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--uuid', required=True)
    args = parser.parse_args()
    result = main(args.uuid)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['stage'] == 'complete' and result['cleanup'] == 'UNMOUNTED' else 1)
