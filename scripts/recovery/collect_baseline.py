"""Read-only Linux baseline. Exports no IPs, UUIDs, credentials or raw logs."""
import datetime
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def run(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 255, ""


def jrun(args):
    code, output = run(args)
    try:
        return json.loads(output) if code == 0 else {}
    except ValueError:
        return {}


def collect():
    mem = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ['MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree']:
            mem[key] = int(value.split()[0])
    ts = jrun(['tailscale', 'status', '--json'])
    prefs = jrun(['tailscale', 'debug', 'prefs'])
    services = {}
    for name in ['ssh', 'tailscaled', 'docker', 'ufw', 'fail2ban', 'unattended-upgrades']:
        services[name] = {field: run(['systemctl', option, name])[1] for field, option in
                          [('active', 'is-active'), ('enabled', 'is-enabled')]}
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    lid = []
    for p in [Path('/etc/systemd/logind.conf'), *Path('/etc/systemd/logind.conf.d').glob('*.conf')]:
        if p.is_file():
            lid += [line.strip() for line in p.read_text().splitlines() if line.strip().startswith(
                ('HandleLidSwitch=', 'HandleLidSwitchExternalPower=', 'HandleLidSwitchDocked='))]
    repos = []
    for parent in [Path.home(), Path.home() / 'projects', Path.home() / 'repos', Path.home() / 'apps']:
        if parent.is_dir():
            for p in parent.iterdir():
                if (p / '.git').exists():
                    # Fixed project labels only; never export arbitrary personal directory names.
                    if p.name.lower() in ['acash', 'pi_personal-infrastructure']:
                        repos.append({'project': p.name, 'head': run(['git', '-C', str(p), 'rev-parse', 'HEAD'])[1],
                                      'dirty': bool(run(['git', '-C', str(p), 'status', '--porcelain'])[1])})
    health_code, health = run(['systemctl', 'is-system-running'])
    failed_code, failed = run(['systemctl', '--failed', '--plain', '--no-legend'])
    return {
        'observedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Live SSH, unprivileged read-only snapshot; not storage restore or Exit Node client E2E',
        'os': release.get('PRETTY_NAME', '').strip('"'), 'kernel': platform.release(),
        'arch': platform.machine(), 'cpus': os.cpu_count(), 'memoryKiB': mem,
        'rootFreeBytes': shutil.disk_usage('/').free,
        'systemHealth': health if health in ['running', 'degraded', 'starting', 'maintenance'] else 'UNKNOWN',
        'failedUnitCount': len(failed.splitlines()) if failed_code == 0 else None,
        'networkWaitOnlineFailed': 'systemd-networkd-wait-online.service' in failed,
        'disks': jrun(['lsblk', '-b', '-J', '-o', 'NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,ROTA,TRAN']),
        'services': services,
        'tools': {t: bool(shutil.which(t)) for t in ['git', 'python3', 'docker', 'ansible', 'lvs', 'ufw', 'fail2ban-client']},
        'tailscale': {'backend': ts.get('BackendState'), 'online': ts.get('Self', {}).get('Online'),
                      'exitNodeOption': ts.get('Self', {}).get('ExitNodeOption'),
                      'defaultRoutesAdvertised': all(r in prefs.get('AdvertiseRoutes', []) for r in ['0.0.0.0/0', '::/0'])},
        'forwarding': {name: Path('/proc/sys/' + name.replace('.', '/')).read_text().strip()
                       for name in ['net.ipv4.ip_forward', 'net.ipv6.conf.all.forwarding']},
        'defaultRouteUsesWifi': 'wlp2s0' in run(['ip', 'route', 'show', 'default'])[1],
        'dnsLookupSucceeded': run(['getent', 'hosts', 'github.com'])[0] == 0,
        'pathsPresent': {p: Path(p).exists() for p in ['/data', '/data/docker', '/data/docker/.env', '/ssd-data', '/var/lib/docker']},
        'explicitLidPolicy': lid, 'knownRepoCheckouts': repos,
        'sudoNoninteractive': run(['sudo', '-n', 'true'])[0] == 0,
        'storageData': 'NOT INSPECTED; privileged read-only mount required',
        'travelUplink': 'OWNER-REPORTED iPad-only; no independent always-on uplink verified',
    }


if __name__ == '__main__':
    print(json.dumps(collect(), indent=2))
