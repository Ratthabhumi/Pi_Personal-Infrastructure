"""Explicit-owner clean-storage operation. One attempt; never called by CI/deploy.

UUID is supplied privately by the staged owner packet, not derived from /dev/sda1.
The partition table, system disk, installer media and Tailscale identity are excluded.
"""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys


class GateError(Exception):
    pass


# lsblk JSON is flat when NAME is omitted unless --tree is explicit. PATH-only
# output is deliberate; require topology rather than relying on a display column.
BLOCK_TREE_COMMAND = ['lsblk', '--tree', '-b', '-p', '-J', '-o',
                      'PATH,TYPE,SIZE,FSTYPE,UUID,MOUNTPOINTS,MAJ:MIN']


def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node.get('children', []))


def validate_target(tree, old_uuid, resolved):
    if not re.fullmatch(r'[a-fA-F0-9-]{36}', old_uuid):
        raise GateError('INVALID_APPROVED_UUID')
    roots = tree.get('blockdevices', [])
    matches = [n for n in flatten(roots) if n.get('uuid') == old_uuid]
    if len(matches) != 1:
        raise GateError('UUID_NOT_UNIQUE')
    target = matches[0]
    if target.get('path') != resolved or target.get('type') != 'part' or target.get('fstype') != 'ext4':
        raise GateError('TARGET_IDENTITY_OR_TYPE_MISMATCH')
    if not 990_000_000_000 <= int(target.get('size', 0)) <= 1_010_000_000_000:
        raise GateError('TARGET_CAPACITY_MISMATCH')
    parents = [n for n in roots if any(c is target for c in n.get('children', []))]
    if len(parents) != 1 or parents[0].get('type') != 'disk':
        raise GateError('PHYSICAL_PARENT_NOT_PROVEN')
    parent = parents[0]
    if len(parent.get('children', [])) != 1 or not 0 <= int(parent['size']) - int(target['size']) < 64 * 1024 * 1024:
        raise GateError('UNEXPECTED_PARTITION_LAYOUT')
    for n in flatten([parent]):
        if any(n.get('mountpoints') or []) or n.get('type') not in ['disk', 'part'] or n.get('fstype') in ['LVM2_member', 'swap', 'vfat']:
            raise GateError('MOUNTED_SYSTEM_LVM_OR_INSTALLER_DISK')
    if target.get('children') or not re.fullmatch(r'\d+:\d+', target.get('maj:min', '')):
        raise GateError('TARGET_HAS_HOLDERS_OR_INVALID_DEVICE_NUMBER')
    return target


def validate_fstab(text, old_uuid, device, evaluated_sources=()):
    if device in evaluated_sources:
        raise GateError('EXISTING_FSTAB_DEVICE_ALIAS_CONFLICT')
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        fields = line.split()
        if len(fields) < 4:
            raise GateError('EXISTING_FSTAB_MALFORMED')
        if fields[1] == '/data' or old_uuid in fields[0] or fields[0] == device or fields[0] == 'LABEL=HOMELAB_DATA':
            raise GateError('EXISTING_FSTAB_TARGET_CONFLICT')


def reject_mounted_device(device_number, lines):
    for line in lines:
        fields = line.split()
        if len(fields) < 3:
            raise GateError('MOUNTINFO_NOT_PARSEABLE')
        if fields[2] == device_number:
            raise GateError('TARGET_MOUNTED_IN_PROCESS_NAMESPACE')


def main(old_uuid, owner):
    report = {'observedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status': 'BLOCKED', 'stage': 'owner-identity', 'checks': {},
              'formatting': 'NOT_EXECUTED', 'foundation': 'NOT_EXECUTED',
              'commands': [], 'uuidPublication': 'Private owner result only; redact before Git'}
    lock = None
    root_state = Path('/var/lib/homelab-clean-20261105')
    private_log = None
    state_safe = False

    def command(args, mutation=False):
        report['commands'].append(args)
        p = subprocess.run(args, capture_output=True, text=True, check=False,
                           timeout=None if mutation else 30)
        if private_log:
            with private_log.open('a') as log:
                log.write(p.stdout + p.stderr)
        if p.returncode:
            report['lastExitCode'] = p.returncode
            raise GateError('COMMAND_FAILED')
        return p.stdout.strip()

    def live_target():
        paths = command(['blkid', '-t', 'UUID=' + old_uuid, '-o', 'device']).splitlines()
        if len(paths) != 1:
            raise GateError('UUID_RESOLUTION_NOT_UNIQUE')
        device = str(Path(paths[0]).resolve(strict=True))
        info = os.stat(device)
        if not stat.S_ISBLK(info.st_mode):
            raise GateError('NOT_BLOCK_DEVICE')
        tree = json.loads(command(BLOCK_TREE_COMMAND))
        target = validate_target(tree, old_uuid, device)
        if command(['blkid', '-p', '-s', 'UUID', '-o', 'value', device]) != old_uuid:
            raise GateError('FRESH_UUID_PROBE_MISMATCH')
        if target['maj:min'] != f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}':
            raise GateError('DEVICE_NUMBER_CHANGED')
        holders = Path('/sys/dev/block') / target['maj:min'] / 'holders'
        if not holders.is_dir() or any(holders.iterdir()):
            raise GateError('BLOCK_DEVICE_HOLDERS')
        # Reject use in another mount namespace, not just this process's findmnt view.
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                lines = (proc / 'mountinfo').read_text().splitlines()
            except (FileNotFoundError, ProcessLookupError):
                continue
            reject_mounted_device(target['maj:min'], lines)
        return target

    try:
        if os.geteuid() != 0 or os.environ.get('SUDO_USER') != owner or not sys.stdin.isatty():
            raise GateError('INTERACTIVE_OWNER_SUDO_REQUIRED')
        account = pwd.getpwnam(owner)
        if owner != 'mew' or account.pw_uid == 0:
            raise GateError('UNEXPECTED_OWNER')
        root_state.mkdir(mode=0o700, exist_ok=True)
        if root_state.is_symlink() or root_state.stat().st_uid != 0 or stat.S_IMODE(root_state.stat().st_mode) != 0o700:
            raise GateError('UNSAFE_ROOT_STATE_DIRECTORY')
        state_safe = True
        lock = (root_state / 'operation.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root_state / 'attempt.json').exists():
            raise GateError('PREVIOUS_ATTEMPT_PRESERVED_DO_NOT_REFORMAT')
        private_log = root_state / f'private-{os.getpid()}.log'
        private_log.touch(mode=0o600, exist_ok=False)
        report['stage'] = 'live-storage-safety-gates'
        target = live_target()
        device = target['path']
        # Block unexpected existing paths/config BEFORE deleting any filesystem data.
        data = Path('/data')
        if data.is_symlink() or os.path.ismount(data) or (data.exists() and (not data.is_dir() or any(data.iterdir()))):
            raise GateError('DATA_MOUNTPOINT_NOT_EMPTY')
        if Path('/etc/fstab').is_symlink():
            raise GateError('FSTAB_SYMLINK_REQUIRES_REVIEW')
        old_fstab = Path('/etc/fstab').read_text()
        # Resolve LABEL/PARTUUID/by-id aliases as well as the explicitly approved UUID.
        # Otherwise formatting could leave an old boot-critical alias entry dangling.
        evaluated = json.loads(command(['findmnt', '--fstab', '--evaluate', '--json', '--output', 'SOURCE,TARGET']))
        sources = []
        for row in flatten(evaluated.get('filesystems', [])):
            source = row.get('source', '').split('[', 1)[0]
            if source.startswith('/dev/'):
                sources.append(str(Path(source).resolve()))
        validate_fstab(old_fstab, old_uuid, device, sources)
        command(['findmnt', '--verify', '--tab-file', '/etc/fstab'])
        # Query may legitimately return 2 when a label is absent.
        label_query = ['blkid', '-t', 'LABEL=HOMELAB_DATA', '-o', 'device']
        report['commands'].append(label_query)
        labels = subprocess.run(label_query, capture_output=True, text=True, check=False)
        if labels.returncode not in [0, 2] or labels.stdout.strip():
            raise GateError('DATA_LABEL_ALREADY_USED_OR_QUERY_FAILED')
        if any(Path(p).exists() or Path(p).is_symlink() for p in ['/etc/docker/daemon.json', '/var/lib/docker', '/usr/sbin/policy-rc.d',
                                        '/etc/apt/sources.list.d/docker.sources', '/etc/apt/sources.list.d/docker.list',
                                        '/etc/apt/keyrings/homelab-docker.asc', '/etc/fstab.homelab-clean.pending',
                                        '/etc/systemd/system/docker.service.d/10-data-mount.conf']):
            raise GateError('EXISTING_DOCKER_STATE_REQUIRES_REVIEW')
        if shutil.which('docker'):
            raise GateError('EXISTING_DOCKER_CLI_REQUIRES_REVIEW')
        for p in ['/etc/docker', '/etc/apt/keyrings', '/etc/apt/sources.list.d', '/etc/systemd/system/docker.service.d']:
            if Path(p).is_symlink():
                raise GateError('CONFIG_DIRECTORY_SYMLINK')
        for p in ['/var/lib/dpkg/lock-frontend', '/var/lib/dpkg/lock', '/var/lib/apt/lists/lock', '/var/cache/apt/archives/lock']:
            if Path(p).exists():
                with Path(p).open('r+') as package_lock:
                    fcntl.lockf(package_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.lockf(package_lock, fcntl.LOCK_UN)
        for service in ['ssh', 'tailscaled']:
            command(['systemctl', 'is-active', '--quiet', service])
        (root_state / 'fstab.before').write_text(old_fstab)
        os.chmod(root_state / 'fstab.before', 0o600)
        report['checks']['oldIdentitySystemDiskInstallerAndMountExclusions'] = 'PASS'
        report['privateOldIdentity'] = {'uuid': old_uuid, 'device': device, 'bytes': target['size']}
        # Re-resolve immediately before the one destructive operation.
        if live_target() != target:
            raise GateError('LIVE_IDENTITY_CHANGED')
        with (root_state / 'attempt.json').open('x') as f:
            json.dump({'authorizedOperation': 'format-only-approved-partition', 'oldUUID': old_uuid,
                       'device': device, 'automaticRetry': False}, f)
        report['stage'] = 'format-approved-partition-once'
        # One -F permits the explicitly authorized overwrite. Never use double -F
        # (mounted/in-use force), repartitioning or secure erase. All gates precede it.
        command(['mkfs.ext4', '-F', '-L', 'HOMELAB_DATA', device], mutation=True)
        report['formatting'] = 'PASS'
        command(['udevadm', 'settle'])
        new_uuid = command(['blkid', '-p', '-s', 'UUID', '-o', 'value', device])
        if not re.fullmatch(r'[a-fA-F0-9-]{36}', new_uuid) or new_uuid == old_uuid:
            raise GateError('NEW_UUID_NOT_VERIFIED')
        if command(['blkid', '-p', '-s', 'TYPE', '-o', 'value', device]) != 'ext4' or command(['blkid', '-p', '-s', 'LABEL', '-o', 'value', device]) != 'HOMELAB_DATA':
            raise GateError('NEW_FILESYSTEM_METADATA_MISMATCH')
        report['privateNewFilesystemUUID'] = new_uuid
        report['stage'] = 'persistent-data-mount'
        data.mkdir(mode=0o755, exist_ok=True)
        # nofail preserves OS/SSH boot if HDD is absent; Docker separately REQUIRES this mount.
        updated = old_fstab.rstrip('\n') + f'\nUUID={new_uuid} /data ext4 defaults,nofail,nodev,nosuid,noatime 0 2\n'
        pending = root_state / 'fstab.pending'
        pending.write_text(updated)
        command(['findmnt', '--verify', '--tab-file', str(pending)])
        if Path('/etc/fstab').read_text() != old_fstab:
            raise GateError('FSTAB_CHANGED_CONCURRENTLY')
        original = Path('/etc/fstab').stat()
        temp = Path('/etc/fstab.homelab-clean.pending')
        with temp.open('x') as f:
            f.write(updated)
        os.chmod(temp, stat.S_IMODE(original.st_mode))
        os.chown(temp, original.st_uid, original.st_gid)
        os.replace(temp, '/etc/fstab')
        command(['systemctl', 'daemon-reload'])
        command(['mount', '/data'])
        mount = json.loads(command(['findmnt', '--mountpoint', '/data', '--json', '--output', 'UUID,FSTYPE,OPTIONS']))['filesystems']
        if len(mount) != 1 or mount[0]['uuid'] != new_uuid or mount[0]['fstype'] != 'ext4' or not {'rw', 'nodev', 'nosuid'}.issubset(mount[0]['options'].split(',')):
            raise GateError('MOUNT_IDENTITY_OR_OPTIONS_MISMATCH')
        for name in ['docker', 'backups', 'acash', 'logs']:
            path = data / name
            path.mkdir(mode=0o700)
            if name == 'logs':
                os.chmod(path, 0o750)
            # Docker, backups and ACASH remain root-only; no account gets broad data access.
        probe = data / '.homelab-write-probe'
        with probe.open('x') as f:
            f.write('synthetic-storage-acceptance')
        if probe.read_text() != 'synthetic-storage-acceptance':
            raise GateError('WRITE_READBACK_MISMATCH')
        probe.unlink()  # Only the file created by this invocation.
        report['checks']['dataMountWriteReadbackCleanup'] = 'PASS'
        report['checks']['fstabStaticValidation'] = 'PASS; actual boot/reboot NOT TESTED'
        report['checks']['directories'] = 'PASS root-owned 0700; logs 0750; no recursive ownership changes'
        report['stage'] = 'minimal-foundation'
        report['foundation'] = 'IN_PROGRESS'
        command(['bash', str(Path(__file__).with_name('provision_foundation.sh')), new_uuid], mutation=True)
        report['foundation'] = 'PASS'
        report['versions'] = {
            'dockerServer': command(['docker', 'version', '--format', '{{.Server.Version}}']),
            'compose': command(['docker', 'compose', 'version', '--short']),
            'ansible': command(['ansible', '--version']).splitlines()[0],
        }
        report['monitoringImageDigests'] = json.loads(command(['docker', 'image', 'inspect', 'prom/node-exporter:v1.8.2', '--format', '{{json .RepoDigests}}']))
        report['stage'] = 'post-change-regression'
        for service in ['ssh', 'tailscaled', 'docker']:
            command(['systemctl', 'is-active', '--quiet', service])
        ts = json.loads(command(['tailscale', 'status', '--json']))
        if not ts.get('Self', {}).get('Online'):
            raise GateError('TAILSCALE_NOT_ONLINE')
        report['checks']['sshTailscaleDockerLocalServiceRegression'] = 'PASS; external SSH and mobile Exit Node egress still require observation'
        report['checks']['acash'] = 'Empty root-only directory; no data, credentials, brokers, jobs or trading deployed'
        report['checks']['exitNodeClientEgress'] = 'NOT TESTED; requires actual external client observation'
        report['status'] = 'PARTIAL'
        report['stage'] = 'storage-and-foundation-complete-hosted-acceptance-pending'
    except Exception as exc:
        report['errorType'] = type(exc).__name__
        report['errorCode'] = str(exc) if isinstance(exc, GateError) else 'PRIVATE_ERROR_REVIEW_REQUIRED'
    finally:
        if state_safe:
            try:
                foundation_state = root_state / 'foundation-checkpoint.json'
                if foundation_state.is_file():
                    report['foundationCheckpoint'] = json.loads(foundation_state.read_text())
                    if report['foundationCheckpoint'].get('status') == 'FAIL':
                        report['foundation'] = 'PARTIAL_FAILED'
                result = root_state / f'result-{os.getpid()}.json'
                with result.open('x') as f:
                    f.write(json.dumps(report, indent=2))
                os.chmod(result, 0o600)
            except OSError:
                pass
        if lock:
            lock.close()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-uuid', required=True)
    parser.add_argument('--owner', default='mew')
    args = parser.parse_args()
    result = main(args.old_uuid, args.owner)
    print(json.dumps(result, indent=2))  # Owner-only result, never publish raw UUID/command metadata to Git.
    raise SystemExit(0 if result['foundation'] == 'PASS' else 1)
