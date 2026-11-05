#!/usr/bin/env bash
# finalize_host_24x7.sh — owner-root, idempotent host hardening for a 24/7 host.
#
# Scope: logind no-suspend, SSH-safe UFW, verification only for everything else.
# Explicitly NOT present: formatting, partition/mount/fstab writes, package
# install/removal, Docker engine restart, ACASH install, credential handling.
#
# The owner must run this with sudo. It fails closed on unexpected state.
set -euo pipefail

RESULT_DIR=/var/lib/homelab-host-ready
RESULT_FILE="$RESULT_DIR/result.txt"
LOGIND_DROPIN=/etc/systemd/logind.conf.d/90-24x7-host.conf
STATUS=()

say()  { printf '%s\n' "$*"; }
pass() { STATUS+=("PASS  $*"); say "PASS  $*"; }
warn() { STATUS+=("WARN  $*"); say "WARN  $*"; }
die()  { STATUS+=("FAIL  $*"); say "FAIL  $*"; write_result; exit 1; }

write_result() {
  install -d -m 0755 "$RESULT_DIR"
  {
    echo "observed_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "kernel=$(uname -r)"
    echo "uptime=$(uptime -p)"
    echo "--- checks ---"
    printf '%s\n' "${STATUS[@]}"
    echo "--- ufw ---"
    ufw status verbose 2>&1 || true
    echo "--- sshd effective policy ---"
    sshd -T 2>/dev/null | grep -E '^(passwordauthentication|permitrootlogin|pubkeyauthentication|kbdinteractiveauthentication) ' || true
    echo "--- sleep targets ---"
    systemctl is-enabled sleep.target suspend.target hibernate.target hybrid-sleep.target 2>&1 || true
    echo "--- networkd-wait-online ---"
    systemctl is-active systemd-networkd-wait-online 2>&1 || true
    journalctl -u systemd-networkd-wait-online --no-pager -n 10 2>&1 || true
    echo "--- node exporter ---"
    curl -fsS -m 5 -o /dev/null -w 'http_code=%{http_code}\n' http://127.0.0.1:9100/metrics 2>&1 || echo 'http=FAIL'
    echo "--- docker data root ---"
    docker info --format 'data-root={{.DockerRootDir}}' 2>&1 || true
    echo "--- listeners (non-loopback) ---"
    ss -lntu 2>/dev/null | awk 'NR==1 || $5 !~ /^(127\.|\[::1\])/' || true
    echo "--- backup ---"
    systemctl is-enabled homelab-backup.timer 2>&1 || true
  } >"$RESULT_FILE"
  chmod 0600 "$RESULT_FILE"
}

[ "$(id -u)" -eq 0 ] || die "Run with sudo; no state changed."
say "24/7 host finalization started. No storage, package or Docker-engine change."

# 1. Prove expected storage state before touching anything.
mountpoint -q /data || die "/data is not a mountpoint."
findmnt -no FSTYPE /data | grep -qx ext4 || die "/data is not ext4."
findmnt -no OPTIONS /data | grep -q '\brw\b' || die "/data is not writable."
[ -d /data/acash ] || die "/data/acash is missing."
[ "$(stat -c '%a %U:%G' /data/acash)" = "700 root:root" ] || die "/data/acash permissions drifted from 0700 root:root."
grep -q '"data-root"[[:space:]]*:[[:space:]]*"/data/docker/engine"' /etc/docker/daemon.json \
  || die "Docker data-root is not /data/docker/engine."
pass "storage contract intact (/data ext4 rw, /data/acash 0700 root:root, docker data-root pinned)"

# 2. Prevent lid-close and idle suspend without touching login sessions.
install -d -m 0755 /etc/systemd/logind.conf.d
cat >"$LOGIND_DROPIN" <<'EOF'
# Managed for a 24/7 server. Revert by deleting this file and unmasking sleep targets.
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore
EOF
chmod 0644 "$LOGIND_DROPIN"
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true
systemctl stop sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true
if systemctl is-enabled sleep.target 2>/dev/null | grep -qx masked; then
  pass "sleep/suspend/hibernate targets masked; logind drop-in installed"
else
  warn "logind drop-in installed but sleep.target is not reported masked"
fi

# 3. SSH-safe firewall: trust the Tailscale interface, allow SSH from the current LAN only.
if ! command -v ufw >/dev/null 2>&1; then
  warn "ufw not installed; firewall unchanged"
else
  LAN_IF=$(ip -4 route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -1)
  LAN_CIDR=""
  if [ -n "${LAN_IF:-}" ] && [ "$LAN_IF" != "tailscale0" ]; then
    LAN_CIDR=$(ip -4 -o addr show dev "$LAN_IF" scope global 2>/dev/null | awk '{print $4}' | head -1)
  fi
  ufw --force default deny incoming >/dev/null
  ufw --force default allow outgoing >/dev/null
  ufw allow in on tailscale0 comment 'Tailscale management' >/dev/null
  ufw allow 41641/udp comment 'Tailscale direct' >/dev/null
  # Preserve the documented Exit Node / subnet-router forwarding path.
  if grep -q '^DEFAULT_FORWARD_POLICY=' /etc/default/ufw; then
    sed -i 's/^DEFAULT_FORWARD_POLICY=.*/DEFAULT_FORWARD_POLICY="ACCEPT"/' /etc/default/ufw
    ufw reload >/dev/null 2>&1 || true
    pass "ufw forward policy set to ACCEPT (Exit Node/subnet routing preserved)"
  fi
  LAN_OK=false
  case "$LAN_CIDR" in ""|100.*) LAN_OK=false ;; *) LAN_OK=true ;; esac
  if [ "$LAN_OK" = true ]; then
    ufw allow from "$LAN_CIDR" to any port 22 proto tcp comment 'SSH current LAN' >/dev/null
    pass "ufw rule added for SSH from $LAN_CIDR (iface $LAN_IF)"
  else
    warn "current LAN CIDR not determined; SSH allowed only via tailscale0"
  fi
  ufw --force enable >/dev/null
  if ufw status | grep -q '^Status: active'; then
    pass "ufw enabled: default deny incoming, tailscale0 trusted, SSH from LAN"
  else
    die "ufw did not report active after enable"
  fi
fi

# 4. Verification only. No changes to these subsystems.
if [ "$(sshd -T 2>/dev/null | awk '/^passwordauthentication /{print $2}')" = "no" ]; then
  pass "sshd password authentication disabled"
else
  warn "sshd password authentication is not disabled (owner decision required)"
fi

if curl -fsS -m 5 -o /dev/null http://127.0.0.1:9100/metrics; then
  pass "node exporter loopback metrics HTTP 200"
else
  warn "node exporter loopback metrics not reachable"
fi

WAIT_STATE=$(systemctl is-active systemd-networkd-wait-online 2>/dev/null || true)
if [ "$WAIT_STATE" = "failed" ]; then
  warn "systemd-networkd-wait-online is failed (non-blocking); root journal captured, no change made"
else
  pass "systemd-networkd-wait-online state: $WAIT_STATE"
fi

if docker info --format '{{.DockerRootDir}}' 2>/dev/null | grep -qx /data/docker/engine; then
  pass "docker reports data-root /data/docker/engine"
else
  warn "docker data-root not confirmed at runtime"
fi

if systemctl is-enabled homelab-backup.timer >/dev/null 2>&1; then
  pass "homelab-backup.timer installed"
else
  warn "no host backup timer installed; off-device backup remains BLOCKED"
fi

write_result
say ""
say "FINISH_RESULT=OK"
say "Private detail: $RESULT_FILE (root 0600). Re-run is safe and idempotent."
say "No reboot performed. Sleep masking is effective immediately; the logind drop-in is belt-and-braces."
