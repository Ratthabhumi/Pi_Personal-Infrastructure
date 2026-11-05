"""Finish the already-created HDD/foundation. No disk formatter or installer.

Diagnoses healthy-in-namespace / unreachable-on-host metrics before the one
allowed container-only repair. Existing format attempt records are never cleared.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

OLD_PROFILE_SHA256 = 'dc2f38857ab4ec45caddd9266b5bc431c9ac0ca6b5c8a8a5b3ddab34e8c44662'
CANDIDATE_SHA256 = '2c976c8608feb9615d07cf3a37ea404956006c2c3cd0ef3accf8f00df1b96b08'
NAME = 'homelab-node-exporter'
IMAGE = 'prom/node-exporter:v1.8.2'
PROBE = '''import json,urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:9100/metrics',timeout=4) as r: text=r.read(4194304).decode()
print(json.dumps({'cpu':'node_cpu_seconds_total' in text,'memory':'node_memory_MemTotal_bytes' in text}))
'''


class Blocked(Exception):
    pass


def metrics(text):
    return 'node_cpu_seconds_total' in text and 'node_memory_MemTotal_bytes' in text


def classify(host_ok, namespace_ok, running, internal, expected_old_profile):
    if host_ok:
        return 'ALREADY_HEALTHY'
    if namespace_ok and running and internal and expected_old_profile:
        return 'HEALTHY_EXPORTER_UNREACHABLE_HOST_BRIDGE_PUBLICATION'
    return 'UNPROVEN_CAUSE_NO_REPAIR'


def validate_container(c, host_network=False):
    if c['Config']['Image'] != IMAGE or c['Config']['User'] != '65534:65534':
        raise Blocked('CONTAINER_IDENTITY_DRIFT')
    h = c['HostConfig']
    if not c['State']['Running'] or c['State'].get('OOMKilled'):
        raise Blocked('CONTAINER_NOT_RUNNING_OR_OOM')
    if not h['ReadonlyRootfs'] or h['Memory'] != 64 * 1024 * 1024 or 'ALL' not in (h.get('CapDrop') or []):
        raise Blocked('CONTAINER_RESOURCE_OR_SECURITY_DRIFT')
    if h.get('PidsLimit') != 64 or h.get('NanoCpus') != 250000000 or not any(s in ['no-new-privileges:true', 'no-new-privileges'] for s in (h.get('SecurityOpt') or [])):
        raise Blocked('CONTAINER_CPU_PID_OR_PRIVILEGE_DRIFT')
    if host_network and (h['NetworkMode'] != 'host' or '--web.listen-address=127.0.0.1:9100' not in c['Config']['Cmd'] or h.get('PortBindings')):
        raise Blocked('LOOPBACK_HOST_NETWORK_NOT_ENFORCED')


def main(expected_uuid):
    report = {'status': 'BLOCKED', 'stage': 'identity', 'formatting': 'NOT_IN_SCOPE_NEVER_INVOKED',
              'repairAttempts': 0, 'checks': {}}
    state = Path('/var/lib/homelab-monitoring-finish-20261105')
    lock = None

    def run(args):
        p = subprocess.run(args, capture_output=True, text=True, timeout=90, check=False)
        if p.returncode:
            report['lastExitCode'] = p.returncode
            raise Blocked('COMMAND_FAILED')
        return p.stdout.strip()

    def inspect():
        return json.loads(run(['docker', 'inspect', NAME]))[0]

    def host_probe():
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open('http://127.0.0.1:9100/metrics', timeout=4) as r:
                return metrics(r.read(4194304).decode())
        except (OSError, ValueError):
            return False

    try:
        if os.geteuid() != 0 or os.environ.get('SUDO_USER') != 'mew' or not sys.stdin.isatty():
            raise Blocked('INTERACTIVE_OWNER_SUDO_REQUIRED')
        if not re.fullmatch(r'[a-fA-F0-9-]{36}', expected_uuid):
            raise Blocked('INVALID_EXPECTED_NEW_UUID')
        report['stage'] = 'existing-storage-and-foundation'
        mount = json.loads(run(['findmnt', '--mountpoint', '/data', '--json', '--output', 'UUID,FSTYPE,OPTIONS']))['filesystems']
        if len(mount) != 1 or mount[0]['uuid'] != expected_uuid or mount[0]['fstype'] != 'ext4' or 'rw' not in mount[0]['options'].split(','):
            raise Blocked('EXISTING_DATA_MOUNT_MISMATCH_NO_CHANGES')
        if run(['docker', 'info', '--format', '{{.DockerRootDir}}']) != '/data/docker/engine':
            raise Blocked('DOCKER_NOT_USING_HDD')
        run(['findmnt', '--verify', '--tab-file', '/etc/fstab'])
        report['checks']['existingHddMountDataRootFstab'] = 'PASS; no storage mutation'
        report['versions'] = {
            'dockerServer': run(['docker', 'version', '--format', '{{.Server.Version}}']),
            'compose': run(['docker', 'compose', 'version', '--short']),
            'ansible': run(['ansible', '--version']).splitlines()[0],
        }
        state.mkdir(mode=0o700, exist_ok=True)
        if state.is_symlink() or state.stat().st_uid != 0 or state.stat().st_mode & 0o077:
            raise Blocked('UNSAFE_FINISH_STATE')
        lock = (state / 'operation.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report['stage'] = 'monitoring-diagnosis'
        c = inspect()
        validate_container(c)
        report['checks']['containerRunningAndBasicLimits'] = 'PASS'
        host_ok = host_probe()
        namespace_ok = False
        internal = False
        for network in c['NetworkSettings'].get('Networks', {}):
            n = json.loads(run(['docker', 'network', 'inspect', network]))[0]
            internal = internal or bool(n.get('Internal'))
        report['checks']['oldInternalNetwork'] = internal
        if not host_ok:
            pid = int(c['State']['Pid'])
            if pid <= 1 or inspect()['State']['Pid'] != pid:
                raise Blocked('CONTAINER_PID_CHANGED')
            # Enter ONLY the known container's network namespace for an HTTP GET.
            # Keep host filesystem and Python; never use this to bypass sudo.
            probe = json.loads(run(['nsenter', '--target', str(pid), '--net', '--', '/usr/bin/python3', '-c', PROBE]))
            namespace_ok = probe.get('cpu') is True and probe.get('memory') is True
        current = Path('/data/docker/minimal/compose.yaml')
        if current.is_symlink():
            raise Blocked('COMPOSE_SYMLINK')
        old_bytes = current.read_bytes()
        old_hash = hashlib.sha256(old_bytes).hexdigest()
        if old_hash not in [OLD_PROFILE_SHA256, CANDIDATE_SHA256]:
            raise Blocked('UNREVIEWED_PROFILE_NO_REPAIR')
        declarative = json.loads(run(['docker', 'compose', '-f', str(current), 'config', '--format', 'json']))
        if c['Config']['Cmd'] != declarative['services']['node-exporter']['command']:
            raise Blocked('RUNTIME_COMMAND_DIFFERS_FROM_PROFILE')
        report['checks']['hostHttpBefore'] = host_ok
        report['checks']['namespaceHttpBefore'] = namespace_ok
        diagnosis = classify(host_ok, namespace_ok, c['State']['Running'], internal, old_hash == OLD_PROFILE_SHA256)
        report['diagnosis'] = diagnosis
        if diagnosis == 'UNPROVEN_CAUSE_NO_REPAIR':
            raise Blocked('UNKNOWN_CAUSE_NO_AUTOMATIC_CHANGE')
        if diagnosis != 'ALREADY_HEALTHY':
            report['stage'] = 'one-monitoring-only-repair'
            if (state / 'repair-attempt.json').exists():
                raise Blocked('PREVIOUS_REPAIR_PRESERVED_NO_RETRY')
            candidate = Path(__file__).with_name('compose.minimal.yaml')
            content = candidate.read_bytes()
            if candidate.is_symlink() or hashlib.sha256(content).hexdigest() != CANDIDATE_SHA256:
                raise Blocked('CANDIDATE_HASH_MISMATCH')
            run(['docker', 'compose', '-f', str(candidate), 'config', '--quiet'])
            with (state / 'compose.before.yaml').open('xb') as backup:
                backup.write(old_bytes)
            with (state / 'repair-attempt.json').open('x') as marker:
                json.dump({'attempts': 1, 'scope': NAME, 'storageOperations': False}, marker)
            pending = current.with_name('compose.monitoring.pending')
            with pending.open('xb') as f:
                f.write(content)
            os.chmod(pending, 0o600)
            os.replace(pending, current)
            report['repairAttempts'] = 1
            run(['docker', 'compose', '-f', str(current), 'up', '--detach', '--no-deps', '--pull', 'never', '--force-recreate', 'node-exporter'])
        report['stage'] = 'post-repair-acceptance'
        for attempt in range(10):
            if host_probe():
                break
            if attempt == 9:
                raise Blocked('HOST_METRICS_STILL_UNHEALTHY_STOP_NO_RETRY')
            time.sleep(2)
        c = inspect()
        validate_container(c, host_network=report['repairAttempts'] == 1)
        listeners = [line.split()[3] for line in run(['ss', '-H', '-lnt']).splitlines()
                     if len(line.split()) > 3 and line.split()[3].endswith(':9100')]
        if not listeners or any(address != '127.0.0.1:9100' for address in listeners):
            # Stop ONLY this service if it is not loopback-bound, never the engine/SSH.
            run(['docker', 'stop', NAME])
            raise Blocked('NON_LOOPBACK_LISTENER_SERVICE_STOPPED')
        for service in ['ssh', 'tailscaled', 'docker']:
            run(['systemctl', 'is-active', '--quiet', service])
        ts = json.loads(run(['tailscale', 'status', '--json']))
        if not ts.get('Self', {}).get('Online'):
            raise Blocked('TAILSCALE_NOT_ONLINE')
        report['checks']['hostMetricsCpuMemoryLoopbackLimits'] = 'PASS'
        report['checks']['sshTailscaleDockerLocalServices'] = 'PASS; external SSH/client egress/reboot require observation'
        report['imageDigests'] = json.loads(run(['docker', 'image', 'inspect', IMAGE, '--format', '{{json .RepoDigests}}']))
        report['resources'] = {'rootFreeBytes': shutil.disk_usage('/').free,
                               'dataFreeBytes': shutil.disk_usage('/data').free}
        report['status'] = 'PARTIAL'
        report['stage'] = 'local-foundation-and-monitoring-pass-external-acceptance-pending'
        report['checks']['acash'] = 'No data/workloads/credentials/trading deployment'
    except Exception as exc:
        report['errorType'] = type(exc).__name__
        report['errorCode'] = str(exc) if isinstance(exc, Blocked) else 'PRIVATE_ERROR_REVIEW_REQUIRED'
    finally:
        if lock:
            lock.close()
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--expected-uuid', required=True)
    r = main(p.parse_args().expected_uuid)
    print(json.dumps(r, indent=2))
    raise SystemExit(0 if r['stage'] == 'local-foundation-and-monitoring-pass-external-acceptance-pending' else 1)
