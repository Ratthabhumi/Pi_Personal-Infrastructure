# PI_HOST_READY_FOR_ACASH — host contract

Date: 5 November 2026
Evidence: [host-audit-20261105.json](evidence/host-audit-20261105.json) (read-only SSH audit), plus accepted storage/monitoring results.

## Verdict

**PI_HOST_READY_FOR_ACASH = HOST_READY**

The Pi/Acer host layer is ready to host a *separately managed* ACASH workload. This verdict covers the host only. It does **not** authorize, install or validate an ACASH collector, scheduler, provider credential, warehouse, research job or trading process. Those remain owned by the ACASH repository and its own approval process.

## What Pi guarantees to ACASH

| Capability | Accepted state |
|---|---|
| OS | Ubuntu 24.04.5 LTS, kernel 6.8.0-139 |
| CPU / RAM | 4 logical CPUs; 3.7 GiB RAM with ~3.1 GiB available |
| Persistent storage | `/data` ext4, 916 GB (870 GB free), `rw,nosuid,nodev,noatime` |
| Mount durability | UUID-based fstab entry with `nofail`; exact-UUID check before Docker starts |
| Docker | Docker CE 29.9.3, Compose v2, data-root `/data/docker/engine`, `live-restore=true`, log rotation 10 MB × 3 |
| Reserved ACASH path | `/data/acash`, `root:root`, mode `0700`, empty |
| Remote management | SSH key auth, `tailscaled` active/enabled |
| Time | `systemd-timesyncd` synchronized; timezone UTC |
| DNS | systemd-resolved working |
| Scheduling | systemd timers operational (17 installed) |
| Metrics | Node Exporter on `127.0.0.1:9100`, HTTP 200 |
| Boot persistence | Docker/SSH/Tailscale enabled; workload containers must use `restart: unless-stopped` |

## Storage contract

- ACASH owns its data layout **below** `/data/acash`. Pi created only the empty, root-only parent directory; it does not prescribe or modify ACASH subdirectories.
- ACASH must not write outside `/data/acash` (logs may also go to journald).
- `/data/docker` belongs to the Docker engine. Do not place ACASH data there.
- `/data/backups` is a same-HDD staging area only. It is **not** off-device backup.
- The filesystem is not encrypted at rest; ACASH must not store broker credentials in plaintext without an ACASH-owned decision on secret storage.

## Resource budget (recommended, enforced by ACASH compose)

- Total ACASH container memory limit ≤ 2 GiB, leaving ≥ 1 GiB for the host.
- Total ACASH CPU limit ≤ 2.0 of 4 logical CPUs.
- Per-container `pids_limit`, `cap_drop: [ALL]`, `no-new-privileges`, and a non-root user.
- Do not mount the Docker socket into ACASH containers.
- Prefer a bounded read-only bind of `/data/acash` only.

## Scheduling semantics for 24/7

- The host runs continuously; that does **not** mean polling every second.
- The collector container should be `restart: unless-stopped`; a systemd unit must be `WantedBy=multi-user.target` and independent of any login session.
- Use market-aware schedules (for example EOD after the US close) and `Persistent=true` timers.
- On start, after network loss or after downtime, the collector must backfill missed dates from the provider. The host does not buffer or replay data for ACASH.
- No ACASH schedule, timer or container is installed by this repository.

## Network contract

- Outbound HTTPS and DNS work from the host.
- Inbound public exposure is not provided. Pi should expose nothing beyond SSH/Tailscale; Node Exporter stays loopback.
- The only WAN uplink is an **iPad hotspot**. If it leaves, 24/7 internet access stops. This is an external dependency, not a software PASS. ACASH must tolerate provider outages and backfill later.

## Not covered here (ACASH-owned work)

- Provider selection, API keys, rate limits and entitlements.
- Market-data schema, warehouse engine, retention and data-quality rules.
- Collector image, version pin, schedule, backfill logic and monitoring dashboards.
- Financial governance: `NO_REAL_ORDERS=true` and zero capital authority remain unchanged.

## Host-side blockers before calling the host production-24/7

1. UFW is disabled while SSH listens on all interfaces. One owner-root action is prepared: [OWNER_DECISION_PACKET.md](OWNER_DECISION_PACKET.md).
2. Default logind policy suspends when the lid closes. The same action masks sleep targets and writes a no-suspend drop-in.
3. No off-device backup exists; see [BACKUP_RECOVERY_CONTRACT.md](BACKUP_RECOVERY_CONTRACT.md).
4. `systemd-networkd-wait-online` is enabled but failed at boot. It is non-blocking (Docker, SSH and metrics are up); root cause needs root journal access. Do not "fix" it by guesswork.
5. `systemd-networkd-wait-online`, UFW, reboot survival, external Exit Node egress and lid-close behaviour are not yet validated until the owner action runs.
