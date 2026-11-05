#!/usr/bin/env bash
# Invoked by the reviewed clean-storage owner operation only, after mount acceptance.
set -Eeuo pipefail
umask 077
phase=prerequisites
trap 'code=$?; printf "{\"status\":\"FAIL\",\"phase\":\"%s\",\"exitCode\":%s,\"line\":%s}\n" "$phase" "$code" "$LINENO" > /var/lib/homelab-clean-20261105/foundation-checkpoint.json; exit "$code"' ERR
test "$(id -u)" = 0
test "$#" = 1
test "$(findmnt --mountpoint /data --noheadings --output UUID)" = "$1"
systemctl is-active --quiet ssh
systemctl is-active --quiet tailscaled
test ! -e /etc/docker/daemon.json
test ! -e /usr/sbin/policy-rc.d
test ! -e /etc/apt/sources.list.d/docker.sources
test ! -e /etc/apt/sources.list.d/docker.list
test ! -e /etc/apt/keyrings/homelab-docker.asc
if command -v docker >/dev/null 2>&1; then
  echo 'BLOCKED: existing Docker installation requires review' >&2
  exit 1
fi
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
test -f "$script_dir/compose.minimal.yaml"

# Avoid default service startup/network changes until Docker's mount/network config exists.
printf '#!/bin/sh\n# homelab-clean-20261105 transient install gate\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 0755 /usr/sbin/policy-rc.d
policy_hash=$(sha256sum /usr/sbin/policy-rc.d | cut -d ' ' -f 1)
cleanup_policy() {
  if test -f /usr/sbin/policy-rc.d && test "$(sha256sum /usr/sbin/policy-rc.d | cut -d ' ' -f 1)" = "$policy_hash"; then
    rm -- /usr/sbin/policy-rc.d  # Only this invocation's newly created, unchanged file.
  fi
}
trap cleanup_policy EXIT
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
phase=ubuntu-foundation-packages
apt-get -o Acquire::Retries=0 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 update
apt-get -o Acquire::Retries=0 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 install -y --no-install-recommends ca-certificates curl gnupg git ansible

# Official Docker Ubuntu repository, signed key; no curl|sh and no blind distro upgrade.
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_CODENAME" = noble
test "$(dpkg --print-architecture)" = amd64
install -d -m 0755 /etc/apt/keyrings /etc/docker /etc/systemd/system/docker.service.d
phase=docker-official-key
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 --connect-timeout 15 --max-time 60 \
  https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/homelab-docker.asc
fingerprint=$(gpg --batch --with-colons --show-keys /etc/apt/keyrings/homelab-docker.asc | awk -F: '$1=="fpr" {print $10; exit}')
test "$fingerprint" = 9DC858229FC7DD38854AE2D88D81803C0EBFCD88
chmod 0644 /etc/apt/keyrings/homelab-docker.asc
printf '%s\n' 'Types: deb' 'URIs: https://download.docker.com/linux/ubuntu' 'Suites: noble' \
  'Components: stable' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/homelab-docker.asc' > /etc/apt/sources.list.d/docker.sources
chmod 0644 /etc/apt/sources.list.d/docker.sources

# Select a private Docker pool disjoint from every currently installed non-default route.
phase=docker-network-and-storage-config
python3 - <<'PY'
import ipaddress,json,subprocess
from pathlib import Path
routes=json.loads(subprocess.run(['ip','-4','-j','route','show','table','all'],capture_output=True,text=True,check=True).stdout)
used=[ipaddress.ip_network(r['dst'],strict=False) for r in routes if r.get('dst') not in [None,'default','0.0.0.0/0']]
choices=[('10.240.0.1/24','10.241.0.0/16',24),('172.28.0.1/24','172.29.0.0/16',24),('192.168.240.1/24','192.168.241.0/24',28)]
for bip,pool,size in choices:
    if all(not ipaddress.ip_network(p,strict=False).overlaps(u) for p in [bip,pool] for u in used):
        config={'data-root':'/data/docker/engine','log-driver':'json-file','log-opts':{'max-size':'10m','max-file':'3'},'live-restore':True,'bip':bip,'default-address-pools':[{'base':pool,'size':size}]}
        with Path('/etc/docker/daemon.json').open('x') as f: json.dump(config,f,indent=2)
        break
else: raise SystemExit('BLOCKED: no non-overlapping Docker pool; do not alter routes')
PY
chmod 0644 /etc/docker/daemon.json
printf '[Unit]\nRequiresMountsFor=/data\n[Service]\nExecStartPre=/usr/bin/findmnt --mountpoint /data --source UUID=%s --types ext4 --noheadings\n' "$1" > /etc/systemd/system/docker.service.d/10-data-mount.conf
chmod 0644 /etc/systemd/system/docker.service.d/10-data-mount.conf
phase=docker-package-installation
apt-get -o Acquire::Retries=0 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 update
apt-get -o Acquire::Retries=0 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 install -y --no-install-recommends \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
phase=docker-config-validation
dockerd --validate --config-file /etc/docker/daemon.json
cleanup_policy
trap - EXIT
systemctl daemon-reload
phase=docker-service-start
systemctl enable --now docker
test "$(docker info --format '{{.DockerRootDir}}')" = /data/docker/engine
test "$(findmnt --target /data/docker/engine --noheadings --output UUID)" = "$1"
systemctl is-active --quiet ssh
systemctl is-active --quiet tailscaled

# Deploy only the explicitly bounded monitoring profile; no historical compose or credentials.
install -d -m 0700 /data/docker/minimal
test ! -e /data/docker/minimal/compose.yaml
install -m 0600 "$script_dir/compose.minimal.yaml" /data/docker/minimal/compose.yaml
docker compose -f /data/docker/minimal/compose.yaml config --quiet
phase=monitoring-image-pull
docker pull prom/node-exporter:v1.8.2
phase=monitoring-start
docker compose -f /data/docker/minimal/compose.yaml up --detach --no-deps --pull never node-exporter
phase=monitoring-http-and-limit-acceptance
python3 - <<'PY'
import json,time,urllib.request,subprocess
# Bounded readiness polling is a health check, never an installation retry.
for attempt in range(10):
    try:
        with urllib.request.urlopen('http://127.0.0.1:9100/metrics',timeout=3) as response:
            text=response.read(4*1024*1024).decode()
        if 'node_memory_MemTotal_bytes' not in text or 'node_cpu_seconds_total' not in text:
            raise ValueError('Expected host CPU/memory collectors missing')
        break
    except (OSError,ValueError):
        if attempt==9: raise SystemExit('BLOCKED: monitoring not healthy; no deployment retry')
        time.sleep(2)
container=json.loads(subprocess.run(['docker','inspect','homelab-node-exporter'],capture_output=True,text=True,check=True).stdout)[0]
assert container['State']['Running']
assert container['HostConfig']['Memory']==64*1024*1024
assert container['HostConfig']['ReadonlyRootfs']
assert container['HostConfig']['PortBindings']['9100/tcp'][0]['HostIp']=='127.0.0.1'
print('MINIMAL_MONITORING_LOCAL_HTTP_AND_LIMITS_PASS')
PY
printf '%s\n' FOUNDATION_PASS
printf '{"status":"PASS","phase":"complete"}\n' > /var/lib/homelab-clean-20261105/foundation-checkpoint.json
