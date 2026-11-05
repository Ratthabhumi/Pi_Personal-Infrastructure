# Homelab recovery report — current result

Date: 5 November 2026. Supersedes the earlier "PARTIAL / MONITORING FAIL" reading; that failure is closed and its evidence is kept for history.

## Current state

| Area | Result | Evidence |
|---|---|---|
| HDD format and `/data` | PASS | accepted owner result; live ext4 rw, 916 GB, 870 GB free |
| fstab and mount durability | PASS | UUID entry, `nofail`, exact-UUID `ExecStartPre` |
| Docker/Compose/Ansible | PASS | installed; Docker CE 29.9.3, Compose v2 |
| Docker data-root | PASS | `/data/docker/engine`, `RequiresMountsFor=/data`, `live-restore=true` |
| SSH / Tailscale / Docker services | PASS | active + enabled |
| Node Exporter | PASS | `127.0.0.1:9100` HTTP 200, non-root, loopback only |
| Time sync / DNS / timers | PASS | timesyncd synchronized; resolved works; 17 timers |
| `/data/acash` | PASS (reserved) | `root:root 0700`, empty |
| 24/7 firewall | **OPEN** | UFW disabled; SSH on all interfaces |
| Closed-lid survival | **OPEN** | logind default suspend |
| Off-device backup | **BLOCKED** | no destination; `/data/backups` is same-HDD |
| Reboot survival | NOT TESTED | requires physical recovery access |
| External Exit Node egress | NOT TESTED | no authorized client observation |
| Independent uplink | BLOCKED | iPad hotspot only |

## Interpretation

The host layer is ready for a separately managed ACASH workload ([PI_HOST_READY_FOR_ACASH.md](PI_HOST_READY_FOR_ACASH.md)). It is not yet "production 24/7" until the owner hardening action runs and reboot/lid/uplink behavior is demonstrated.

The historical monitoring failure, its diagnosis and the accepted service-only repair remain documented in [monitoring-failure-20261105.json](evidence/monitoring-failure-20261105.json), [monitoring-finish-preparation-20261105.json](evidence/monitoring-finish-preparation-20261105.json) and [STORAGE_RECOVERY_REPORT.md](STORAGE_RECOVERY_REPORT.md). Nothing was reformatted, reinstalled or rolled back.

## Next actions

1. Owner runs `Invoke-OwnerHostReady.ps1` from [OWNER_DECISION_PACKET.md](OWNER_DECISION_PACKET.md).
2. Reboot with physical access, then re-verify services and closed-lid behaviour.
3. Choose an off-device backup destination.
4. Deploy ACASH from the ACASH repository, not this one.
