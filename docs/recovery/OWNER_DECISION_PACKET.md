# One action — 24/7 host hardening (root)

Monitoring is PASS. Do **not** run `Invoke-OwnerClean.ps1` or `Invoke-OwnerFinish.ps1` again. No formatting, package install or Docker restart is involved.

## Why

Live audit found two production blockers for a 24/7 host:

1. UFW is disabled (`ENABLED=no`) while SSH listens on `0.0.0.0:22`.
2. The default logind policy suspends when the lid closes.

## Command

Run in Windows PowerShell from this checkout:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Users\MewMew\.codex\worktrees\homelab-recovery\Pi_Personal-Infrastructure\scripts\recovery\Invoke-OwnerHostReady.ps1"
```

Owner sudo is required; enter the password locally only. The wrapper uploads [finalize_host_24x7.sh](../../scripts/recovery/finalize_host_24x7.sh) over the verified Tailscale peer, runs it with `sudo`, and removes the temporary upload.

## What it changes

- Writes `/etc/systemd/logind.conf.d/90-24x7-host.conf` and masks `sleep/suspend/hibernate/hybrid-sleep` targets. Effective immediately; reversible with `systemctl unmask` plus removing the drop-in.
- Enables UFW with default deny incoming, trusts `tailscale0`, allows Tailscale UDP 41641 and SSH 22 only from the current LAN CIDR. Existing sessions survive via conntrack. `DEFAULT_FORWARD_POLICY` is set to `ACCEPT` because this host advertises an Exit Node/subnet route; without it, forwarded client traffic would break. No Docker restart happens.
- Verification only: SSH password policy, Node Exporter, Docker data-root, `systemd-networkd-wait-online`, backup timer. It does **not** restart Docker, change mounts, or install packages.

## Fail-closed behavior

It stops before any change unless `/data` is ext4 rw, `/data/acash` is `0700 root:root`, Docker data-root is `/data/docker/engine`, and the exact backup line is intact.

## After it runs

Send only the `FINISH_RESULT` summary. Then separately: reboot with physical recovery access, confirm SSH/Tailscale/Docker/metrics return, and confirm closed-lid survival. Off-device backup remains BLOCKED until an owner destination exists.
