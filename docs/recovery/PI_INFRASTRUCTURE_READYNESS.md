# Pi readiness — actual progress

Date: 5 November 2026. Evidence: [host-audit-20261105.json](evidence/host-audit-20261105.json) (read-only SSH) plus accepted owner storage/monitoring results.

PASS — storage: approved format, UUID-backed writable `/data` (916 GB, 870 GB free, ext4 `rw,nosuid,nodev,noatime`), validated fstab, synthetic I/O, narrow directory permissions. Original system/installer disks preserved.

PASS — foundation: Docker CE 29.9.3, Compose v2, Ansible installed; Docker/SSH/Tailscale active and enabled. Docker data-root `/data/docker/engine` with an exact-UUID mount dependency and `live-restore=true`.

PASS — monitoring: Node Exporter answers `http://127.0.0.1:9100/metrics` with HTTP 200 on loopback only, running as `nobody` with a reduced collector set. The earlier monitoring failure is closed; the historical failure evidence is retained.

PASS — host services: time synchronized (`systemd-timesyncd`), DNS resolution works, systemd timers operational, 3.1 GiB RAM available.

PASS — ACASH host contract: `PI_HOST_READY_FOR_ACASH = HOST_READY`. See [PI_HOST_READY_FOR_ACASH.md](PI_HOST_READY_FOR_ACASH.md). No ACASH application is installed by this repository.

OPEN — host 24/7 hardening: UFW is currently disabled while SSH listens on all interfaces, and the default logind policy suspends on lid close. One owner-root action is prepared in [OWNER_DECISION_PACKET.md](OWNER_DECISION_PACKET.md). Not yet executed or verified.

OPEN — backup: no off-device destination; `/data/backups` is same-HDD only. See [BACKUP_RECOVERY_CONTRACT.md](BACKUP_RECOVERY_CONTRACT.md).

OPEN — external dependency: the only WAN uplink is an iPad hotspot. If it leaves, 24/7 internet access stops. This is not a software PASS.

NOT TESTED: reboot survival, external Exit Node client egress, closed-lid behaviour after hardening, off-device restore, independent home uplink.

Local foundation is READY at the host layer; 24/7 production status stays PENDING until the owner hardening action runs and reboot/uplink conditions are demonstrated. ACASH integration is not production or trading authority.
